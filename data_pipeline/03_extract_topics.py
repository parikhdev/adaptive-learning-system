"""
PURPOSE:
    Assign two parameterized fields to every question in difficulty_scored.csv:
        1. topic — primary JEE/NEET syllabus chapter (e.g., "Electrostatics")
        2. subtopic — refined sub-category within topic (e.g., "Capacitors")
DETECTION STRATEGY
    Layer 1: English keyword matching (case-insensitive substring)
    Layer 2: LaTeX command pattern matching (for formula-heavy questions)
    Within each layer, topics are evaluated in PRIORITY ORDERR

    If no topic matches: topic = "General", subtopic = "General"
INPUTS:
    data/processed/difficulty_scored.csv       (from 02_score_difficulty.py)
OUTPUTS:
    data/processed/topics_extracted.csv        — full dataset with topic + subtopic
    data/reports/topic_report.json             — coverage and distribution audit
"""

import os
import re
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)



#   TAXONOMY[subject] = [
#       (topic_name, subtopic_name, [keyword_list], is_regex),
#       ...
#   ]
TAXONOMY: dict[str, list[tuple]] = {
    # PHYSICS — JEE/NEET Syllabus Chapters
    "Physics": [
        # Modern Physics (most specific keywords first) 
        ("Modern Physics", "Photoelectric Effect",
         ["photoelectric", "photon", "work function", "threshold frequency", "einstein equation"], False),
        ("Modern Physics", "Atomic Structure",
         ["bohr model", "bohr's model", "hydrogen spectrum", "balmer", "lyman", "paschen", "rydberg"], False),
        ("Modern Physics", "Nuclear Physics",
         ["nuclear fission", "nuclear fusion", "radioactive", "half life", "alpha decay", "beta decay",
          "gamma ray", "binding energy", "mass defect", "neutron separation", "atomic mass unit"], False),
        ("Modern Physics", "De Broglie & Quantum",
         ["de broglie", "wave function", "heisenberg", "uncertainty principle", "quantum", "wave-particle"], False),
        ("Modern Physics", "X-Rays",
         ["x-ray", "x ray", "moseley", "bragg"], False),

        # Semiconductors 
        ("Semiconductors", "Logic Gates",
         ["logic gate", "nand", "nor gate", "and gate", "or gate", "xor", "boolean"], False),
        ("Semiconductors", "Transistors",
         ["transistor", "bjt", "mosfet", "emitter", "collector", "base current", "amplifier"], False),
        ("Semiconductors", "Diodes",
         ["p-n junction", "zener diode", "diode", "rectifier", "forward bias", "reverse bias"], False),
        ("Semiconductors", "Semiconductor Materials",
         ["semiconductor", "doping", "n-type", "p-type", "intrinsic", "extrinsic", "silicon", "germanium"], False),

        # Optics 
        ("Optics", "Wave Optics",
         ["interference", "diffraction", "polarization", "polarisation", "young's double slit",
          "ydse", "single slit", "coherent", "fringe width", "brewster"], False),
        ("Optics", "Optical Instruments",
         ["microscope", "telescope", "magnification", "eyepiece", "objective lens"], False),
        ("Optics", "Ray Optics",
         ["lens", "mirror", "refraction", "reflection", "snell", "total internal reflection",
          "prism", "critical angle", "refractive index", "focal length", "optical fiber",
          "concave", "convex", "power of lens", "lens maker"], False),
        ("Optics", "Spectrum & Color",
         ["dispersion", "spectrum", "wavelength", "visible light", "ultraviolet", "infrared",
          "electromagnetic spectrum", "colour", "color"], False),

        # Waves & Sound 
        ("Waves", "Sound Waves",
         ["sound", "doppler", "echo", "sonic", "ultrasonic", "decibel", "loudness", "pitch"], False),
        ("Waves", "Standing Waves",
         ["standing wave", "stationary wave", "node", "antinode", "harmonics", "overtone"], False),
        ("Waves", "Wave Motion",
         ["wave", "frequency", "amplitude", "wavelength", "time period", "wave speed",
          "transverse wave", "longitudinal wave", "progressive wave", "resonance"], False),

        # Magnetism & EMI 
        ("Magnetism & EMI", "Electromagnetic Induction",
         ["faraday", "lenz", "electromagnetic induction", "induced emf", "motional emf",
          "flux linkage", "mutual inductance"], False),
        ("Magnetism & EMI", "Alternating Current",
         ["alternating current", "ac circuit", "impedance", "reactance", "resonance frequency",
          "transformer", "rms", "power factor", "lcr", "rc circuit", "rl circuit"], False),
        ("Magnetism & EMI", "Magnetic Materials",
         ["ferromagnetic", "paramagnetic", "diamagnetic", "permeability", "hysteresis",
          "magnetic susceptibility", "curie"], False),
        ("Magnetism & EMI", "Magnetostatics",
         ["magnetic field", "magnetic flux", "biot-savart", "ampere", "solenoid",
          "toroid", "bar magnet", "magnetic moment", "earth magnet", "magnetic dipole"], False),

        # Current Electricity 
        ("Current Electricity", "Kirchhoff Laws",
         ["kirchhoff", "kvl", "kcl", "loop rule", "junction rule"], False),
        ("Current Electricity", "Wheatstone Bridge",
         ["wheatstone", "potentiometer", "meter bridge", "balanced bridge"], False),
        ("Current Electricity", "Cells & Batteries",
         ["battery", "emf", "internal resistance", "terminal voltage", "cell combination",
          "series cells", "parallel cells", "charging", "discharging"], False),
        ("Current Electricity", "Electric Circuits",
         ["current", "resistance", "resistivity", "ohm", "conductor", "resistor",
          "series resistance", "parallel resistance", "drift velocity", "electric power",
          "heating effect", "joule"], False),

        # Electrostatics 
        ("Electrostatics", "Capacitors",
         ["capacitor", "capacitance", "dielectric", "farad", "energy stored", "charging capacitor",
          "parallel plate", "spherical capacitor", "cylindrical capacitor"], False),
        ("Electrostatics", "Electric Potential",
         ["potential difference", "electric potential", "equipotential", "potential energy",
          "work done by electric field"], False),
        ("Electrostatics", "Gauss Law",
         ["gauss", "electric flux", "gaussian surface"], False),
        ("Electrostatics", "Coulombs Law",
         ["coulomb", "electric charge", "electric force", "test charge"], False),
        ("Electrostatics", "Electric Field",
         ["electric field", "field lines", "dipole", "electric dipole", "permittivity"], False),

        # Thermodynamics 
        ("Thermodynamics", "Kinetic Theory",
         ["kinetic theory", "rms speed", "mean free path", "degrees of freedom",
          "equipartition", "vrms", "vmost probable", "maxwell"], False),
        ("Thermodynamics", "Heat Transfer",
         ["conduction", "convection", "radiation", "stefan", "newton's law of cooling",
          "thermal conductivity", "black body", "wien"], False),
        ("Thermodynamics", "Laws of Thermodynamics",
         ["carnot", "second law", "first law", "zeroth law", "entropy", "thermodynamic process",
          "heat engine", "refrigerator", "coefficient of performance"], False),
        ("Thermodynamics", "Thermal Expansion",
         ["thermal expansion", "coefficient of expansion", "linear expansion", "volume expansion",
          "specific heat", "latent heat", "calorimetry"], False),
        ("Thermodynamics", "Temperature & Heat",
         ["temperature", "heat", "isothermal", "adiabatic", "isobaric", "isochoric",
          "internal energy", "kelvin", "celsius", "thermometer"], False),

        # Mechanics — Fluid & Properties 
        ("Properties of Matter", "Fluid Mechanics",
         ["bernoulli", "venturi", "viscosity", "stokes", "terminal velocity",
          "surface tension", "capillary", "buoyancy", "archimedes", "fluid pressure",
          "pascal", "hydraulic"], False),
        ("Properties of Matter", "Elasticity",
         ["young's modulus", "bulk modulus", "shear modulus", "stress", "strain",
          "elastic limit", "hooke's law", "poisson ratio"], False),

        # Mechanics — Core 
        ("Mechanics", "Simple Harmonic Motion",
         ["simple harmonic", "shm", "pendulum", "spring mass", "time period of pendulum",
          "restoring force", "angular frequency shm"], False),
        ("Mechanics", "Gravitation",
         ["gravitation", "gravitational", "satellite", "escape velocity", "orbital velocity",
          "kepler", "geostationary", "universal gravitation"], False),
        ("Mechanics", "Rotation",
         ["moment of inertia", "angular momentum", "torque", "angular velocity",
          "angular acceleration", "rolling", "rotational kinetic energy", "radius of gyration"], False),
        ("Mechanics", "Work, Energy & Power",
         ["work done", "kinetic energy", "potential energy", "conservation of energy",
          "work energy theorem", "power", "collision", "elastic collision", "inelastic"], False),
        ("Mechanics", "Laws of Motion",
         ["newton", "force", "friction", "acceleration", "inertia", "pseudo force",
          "free body diagram", "normal force", "tension", "fbd"], False),
        ("Mechanics", "Kinematics",
         ["velocity", "displacement", "motion", "projectile", "trajectory", "uniform motion",
          "non uniform", "relative motion", "distance", "speed"], False),

        # LaTeX-based patterns (regex) for formula-heavy Physics
        # [\\x5c] reliably matches one literal backslash as stored in CSV text.
        ("Mechanics", "Kinematics",
         [r"[\\x5c]vec\{v\}", r"[\\x5c]vec\{u\}"], True),
    ],

    # CHEMISTRY — JEE/NEET Syllabus Chapters
    "Chemistry": [
        # Organic — Specific reactions first 
        ("Organic Chemistry", "Named Reactions",
         ["aldol", "cannizzaro", "clemmensen", "wolff-kishner", "grignard", "diels-alder",
          "beckmann", "hofmann", "gabriel", "reimer-tiemann", "kolbe", "sandmeyer",
          "williamson", "claisen", "friedel-crafts", "baeyer"], False),
        ("Organic Chemistry", "Biomolecules",
         ["glucose", "fructose", "sucrose", "cellulose", "starch", "glycogen",
          "amino acid", "peptide bond", "protein structure", "enzyme", "dna structure",
          "rna structure", "nucleotide", "purine", "pyrimidine", "vitamins", "hormone"], False),
        ("Organic Chemistry", "Polymers",
         ["polymer", "monomer", "polymerization", "addition polymer", "condensation polymer",
          "nylon", "bakelite", "teflon", "pvc", "natural rubber", "synthetic rubber"], False),
        ("Organic Chemistry", "Amines & Nitrogen",
         ["amine", "diazonium", "nitro compound", "nitrile", "amide", "isocyanate",
          "coupling reaction", "nitrogen compound"], False),
        ("Organic Chemistry", "Carbonyl Compounds",
         ["aldehyde", "ketone", "carbonyl", "iupac name", "nucleophilic addition",
          "tollen", "fehling", "benedict", "2,4-dnp"], False),
        ("Organic Chemistry", "Carboxylic Acids",
         ["carboxylic acid", "acetic acid", "butyric acid", "formic acid", "oxalic",
          "ester", "saponification", "acid chloride", "anhydride"], False),
        ("Organic Chemistry", "Alcohols & Ethers",
         ["alcohol", "phenol", "ether", "glycol", "glycerol", "dehydration",
          "lucas test", "victor meyer", "alcohol oxidation"], False),
        ("Organic Chemistry", "Hydrocarbons",
         ["alkane", "alkene", "alkyne", "arene", "aromatic", "benzene", "toluene",
          "naphthalene", "markovnikov", "anti-markovnikov", "hydrogenation",
          "halogenation", "combustion", "cracking"], False),
        ("Organic Chemistry", "Isomerism",
         ["isomer", "structural isomer", "stereo isomer", "geometric isomer", "optical isomer",
          "enantiomer", "diastereomer", "chirality", "chiral center", "r-s configuration"], False),
        ("Organic Chemistry", "Reaction Mechanisms",
         ["nucleophile", "electrophile", "sn1", "sn2", "e1", "e2", "carbocation",
          "carbanion", "free radical", "addition reaction", "elimination reaction",
          "substitution reaction"], False),
        ("Organic Chemistry", "General Organic",
         ["organic", "carbon compound", "functional group", "homologous series",
          "iupac", "constitutional", "organic chemistry"], False),

        # Physical Chemistry 
        ("Electrochemistry", "Electrolysis",
         ["electrolysis", "faraday's law", "electroplating", "electric furnace",
          "electrode reaction", "discharge"], False),
        ("Electrochemistry", "Galvanic Cells",
         ["galvanic", "daniel cell", "fuel cell", "standard electrode potential",
          "reduction potential", "nernst equation", "emf of cell",
          "cell notation", "anode", "cathode"], False),
        ("Chemical Kinetics", "Rate Laws",
         ["rate law", "rate constant", "order of reaction", "zero order", "first order",
          "second order", "half life", "integrated rate", "molecularity"], False),
        ("Chemical Kinetics", "Activation Energy",
         ["activation energy", "arrhenius", "threshold energy", "temperature dependence",
          "collision theory", "transition state"], False),
        ("Surface Chemistry", "Adsorption & Catalysis",
         ["adsorption", "absorption", "colloid", "sol", "gel", "emulsion",
          "tyndall", "brownian motion", "coagulation", "catalyst", "catalysis",
          "enzyme catalysis", "freundlich"], False),
        ("Chemical Equilibrium", "Ionic Equilibrium",
         ["buffer", "solubility product", "ksp", "henderson", "common ion effect",
          "degree of dissociation", "weak acid", "weak base", "hydrolysis"], False),
        ("Chemical Equilibrium", "Chemical Equilibrium",
         ["equilibrium constant", "le chatelier", "kp", "kc", "reaction quotient",
          "homogeneous equilibrium", "heterogeneous equilibrium"], False),
        ("Thermodynamics", "Thermochemistry",
         ["enthalpy", "hess", "bond energy", "heat of formation", "heat of combustion",
          "lattice energy", "born-haber", "heat of neutralization"], False),
        ("Thermodynamics", "Thermodynamic Laws",
         ["entropy", "gibbs", "free energy", "spontaneous", "second law", "third law",
          "helmholtz", "work function"], False),
        ("Solutions", "Colligative Properties",
         ["colligative", "elevation in boiling point", "depression in freezing point",
          "osmotic pressure", "van't hoff", "relative lowering", "ebullioscopy"], False),
        ("Solutions", "Solutions & Concentration",
         ["molarity", "molality", "normality", "mole fraction", "solubility",
          "henry's law", "raoult's law", "ideal solution", "non ideal"], False),
        ("Atomic Structure", "Quantum Numbers",
         ["quantum number", "principal quantum", "azimuthal", "magnetic quantum",
          "spin quantum", "aufbau", "hund", "pauli", "orbital filling"], False),
        ("Atomic Structure", "Atomic Models",
         ["bohr model", "rutherford", "thomson model", "nuclear model",
          "emission spectrum", "absorption spectrum", "balmer", "paschen"], False),
        ("Mole Concept", "Stoichiometry",
         ["stoichiometry", "limiting reagent", "theoretical yield", "percentage yield",
          "empirical formula", "molecular formula"], False),
        ("Mole Concept", "Mole Concept",
         ["mole", "avogadro", "molar mass", "gram equivalent", "equivalent weight",
          "mole fraction", "mass percent"], False),

        # Inorganic Chemistry 
        ("Inorganic Chemistry", "d & f Block",
         ["d-block", "f-block", "transition metal", "inner transition",
          "lanthanide", "actinide", "oxidation state", "variable valency",
          "colored compound", "catalyst property"], False),
        ("Inorganic Chemistry", "Coordination Compounds",
         ["coordination compound", "coordination complex", "ligand", "central metal",
          "coordination number", "crystal field", "cfse", "spectrochemical", "isomerism complex",
          "iupac nomenclature complex", "ambidentate", "chelate", "edta"], False),
        ("Inorganic Chemistry", "p-Block Elements",
         ["p-block", "group 13", "group 14", "group 15", "group 16", "group 17", "group 18",
          "nitrogen family", "oxygen family", "halogen", "noble gas", "boron", "carbon family",
          "silicate", "phosphorus", "sulphur", "chlorine", "interhalogen"], False),
        ("Inorganic Chemistry", "s-Block Elements",
         ["s-block", "alkali metal", "alkaline earth", "group 1", "group 2",
          "sodium", "potassium", "calcium", "magnesium", "lithium",
          "diagonal relationship", "anomalous behavior"], False),
        ("Inorganic Chemistry", "Metallurgy",
         ["metallurgy", "ore", "mineral", "gangue", "flux", "slag", "smelting",
          "roasting", "calcination", "refining", "electrolytic refining", "extraction of metal"], False),
        ("Inorganic Chemistry", "Chemical Bonding",
         ["covalent bond", "ionic bond", "metallic bond", "hydrogen bond",
          "van der waals", "dipole moment", "electronegativity", "polarity",
          "fajan", "vsepr", "hybridization", "sigma bond", "pi bond",
          "molecular orbital", "bond order", "resonance"], False),
        ("Inorganic Chemistry", "Periodic Table",
         ["periodic table", "periodic law", "periodicity", "atomic radius",
          "ionic radius", "ionization energy", "electron affinity",
          "electronegativity trend", "shielding", "effective nuclear charge",
          "periodic property", "valence electron"], False),

        # Environmental & Analytical 
        ("Environmental Chemistry", "Pollution",
         ["pollution", "pollutant", "acid rain", "ozone depletion", "greenhouse",
          "smog", "eutrophication", "heavy metal", "bod", "cod"], False),
    ],

    # MATHS — JEE/NEET Syllabus Chapters
    "Maths": [
        # Calculus
        ("Calculus", "Differential Equations",
         ["differential equation", "d.e.", "de whose", "particular solution",
          "general solution", "variable separable", "linear differential", "homogeneous de"], False),
        ("Calculus", "Applications of Derivatives",
         ["maxima", "minima", "maximum", "minimum", "rate of change",
          "tangent to curve", "normal to curve", "increasing function", "decreasing function",
          "rolle's theorem", "mean value theorem", "lagrange"], False),
        ("Calculus", "Definite Integrals",
         ["definite integral", "area under curve", "area bounded",
          "properties of definite", "fundamental theorem"], False),
        ("Calculus", "Indefinite Integrals",
         ["integration by parts", "integration by substitution",
          "integration of rational", "partial fraction", "trigonometric integral",
          "reduction formula", "indefinite integral"], False),
        ("Calculus", "Limits & Continuity",
         ["limit", "continuity", "differentiability", "left hand limit",
          "right hand limit", "l'hopital", "sandwich theorem", "squeeze theorem"], False),
        ("Calculus", "Differentiation",
         ["derivative", "differentiation", "chain rule", "product rule",
          "quotient rule", "implicit differentiation", "parametric differentiation",
          "second derivative", "higher derivative"], False),
        # LaTeX-based Calculus detection
        # [\\x5c] matches single literal backslash character in CSV text
        ("Calculus", "Integration",
         [r"[\\x5c]int(?!o|e|r)", r"[\\x5c]oint", r"[\\x5c]iint"], True),
        ("Calculus", "Differentiation",
         [r"[\\x5c]frac\{d", r"[\\x5c]partial", r"[\\x5c]nabla"], True),
        ("Calculus", "Limits",
         [r"[\\x5c]lim(?!it)", r"[\\x5c]infty"], True),

        # Algebra 
        ("Algebra", "Complex Numbers",
         ["complex number", "argand plane", "de moivre", "modulus of complex",
          "argument of complex", "polar form", "imaginary part", "real part",
          "conjugate", "complex root"], False),
        ("Algebra", "Sequences & Series",
         ["arithmetic progression", "geometric progression", "harmonic progression",
          "ap", "gp", "hp", "sum of series", "nth term", "arithmetic mean",
          "geometric mean", "harmonic mean", "sum to infinity"], False),
        ("Algebra", "Binomial Theorem",
         ["binomial theorem", "binomial expansion", "binomial coefficient",
          "general term", "middle term", "binomial series"], False),
        ("Algebra", "Determinants & Matrices",
         ["determinant", "matrix", "inverse of matrix", "transpose", "adjoint",
          "rank of matrix", "singular matrix", "eigenvalue", "system of equations",
          "cramer's rule", "row reduction"], False),
        ("Algebra", "Mathematical Induction",
         ["mathematical induction", "principle of induction", "inductive step",
          "base case", "induction hypothesis", "sigma notation"], False),
        ("Algebra", "Quadratic Equations",
         ["quadratic equation", "quadratic formula", "discriminant",
          "nature of roots", "sum of roots", "product of roots",
          "quadratic polynomial", "roots of equation"], False),
        # LaTeX-based Algebra
        ("Algebra", "Polynomial Algebra",
         [r"x\^[2-9]", r"[\\x5c]sqrt\{", r"[\\x5c]frac\{(?![dD])"], True),

        # Trigonometry 
        ("Trigonometry", "Inverse Trigonometry",
         ["inverse trigonometric", "arcsin", "arccos", "arctan",
          "arc sin", "arc cos", "principal value", "range of inverse"], False),
        ("Trigonometry", "Properties of Triangles",
         ["sine rule", "cosine rule", "law of sines", "law of cosines",
          "circumradius", "inradius", "area of triangle", "half angle formula",
          "properties of triangle"], False),
        ("Trigonometry", "Trigonometric Equations",
         ["trigonometric equation", "general solution", "principal solution",
          "sin theta equal", "cos theta equal"], False),
        ("Trigonometry", "Trigonometric Identities",
         ["trigonometric identity", "pythagorean identity", "double angle",
          "half angle", "sum to product", "product to sum", "compound angle",
          "addition formula", "sin a+b", "cos a+b", "tan a+b"], False),
        ("Trigonometry", "Trigonometry",
         ["trigonometric", "trigonometry", "sine", "cosine", "tangent",
          "secant", "cosecant", "cotangent", "angle of elevation",
          "angle of depression", "bearing", "radian", "degree"], False),
        # LaTeX-based Trigonometry
        ("Trigonometry", "Trigonometry",
         [r"[\\x5c]sin", r"[\\x5c]cos", r"[\\x5c]tan", r"[\\x5c]sec",
          r"[\\x5c]csc", r"[\\x5c]cot", r"[\\x5c]arcsin",
          r"[\\x5c]arccos", r"[\\x5c]arctan", r"[\\x5c]theta"], True),

        # Coordinate Geometry 
        ("Coordinate Geometry", "3D Geometry",
         ["three dimensional", "3d geometry", "direction cosine", "direction ratio",
          "plane equation", "line in 3d", "skew lines", "angle between planes",
          "distance from plane", "foot of perpendicular"], False),
        ("Coordinate Geometry", "Conic Sections",
         ["parabola", "ellipse", "hyperbola", "conic section", "focus", "directrix",
          "eccentricity", "latus rectum", "tangent to conic", "normal to conic",
          "chord of contact", "pair of tangents"], False),
        ("Coordinate Geometry", "Circles",
         ["circle", "centre of circle", "radius", "chord", "tangent to circle",
          "normal to circle", "power of point", "radical axis",
          "family of circles", "common tangent", "concentric"], False),
        ("Coordinate Geometry", "Straight Lines",
         ["straight line", "slope", "intercept", "collinear", "concurrent",
          "angle between lines", "distance from line", "midpoint",
          "section formula", "locus", "equation of line"], False),
        # LaTeX-based Coordinate Geometry
        ("Coordinate Geometry", "Vectors in 3D",
         [r"[\\x5c]vec\{r\}", r"[\\x5c]overrightarrow", r"[\\x5c]hat\{i\}",
          r"[\\x5c]hat\{j\}", r"[\\x5c]hat\{k\}", r"[\\x5c]overline\{r\}"], True),

        # Vectors 
        ("Vectors", "Vector Operations",
         ["vector", "dot product", "cross product", "scalar product", "vector product",
          "projection of vector", "angle between vectors", "unit vector",
          "position vector", "collinear vectors", "coplanar vectors"], False),
        # LaTeX-based Vectors
        ("Vectors", "Vector Operations",
         [r"[\\x5c]vec\{", r"[\\x5c]cdot", r"[\\x5c]overrightarrow\{"], True),

        # Probability & Statistics 
        ("Probability", "Bayes Theorem",
         ["bayes theorem", "bayes' theorem", "conditional probability",
          "posterior probability", "prior probability", "total probability"], False),
        ("Probability", "Random Variables",
         ["random variable", "probability distribution", "binomial distribution",
          "poisson distribution", "normal distribution", "expectation", "variance",
          "standard deviation"], False),
        ("Probability", "Probability",
         ["probability", "permutation", "combination", "favourable outcome",
          "sample space", "mutually exclusive", "independent event",
          "complement", "addition theorem", "multiplication theorem"], False),

        # Sets, Relations & Functions
        ("Sets & Functions", "Functions",
         ["function", "domain", "range", "codomain", "bijection", "injection",
          "surjection", "one-one", "onto", "composite function", "inverse function",
          "even function", "odd function", "periodic function"], False),
        ("Sets & Functions", "Sets & Relations",
         ["set", "subset", "union", "intersection", "complement of set",
          "cartesian product", "relation", "equivalence relation",
          "reflexive", "symmetric", "transitive"], False),

        # Mathematical Reasoning 
        ("Mathematical Reasoning", "Logic",
         ["statement", "negation", "conjunction", "disjunction", "implication",
          "biconditional", "tautology", "contradiction", "contrapositive",
          "converse", "inverse statement"], False),
    ],

    # BIOLOGY — JEE/NEET Syllabus Chapters
    "Biology": [
        # Genetics & Molecular Biology 
        ("Genetics", "Biotechnology",
         ["recombinant dna", "restriction enzyme", "pcr", "gel electrophoresis",
          "cloning", "transgenic", "genetically modified", "biopharming",
          "gene therapy", "bioreactor", "fermentation technology"], False),
        ("Genetics", "Molecular Genetics",
         ["dna replication", "transcription", "translation", "mrna", "trna",
          "rrna", "codon", "anticodon", "genetic code", "operon",
          "lac operon", "trp operon", "promoter", "repressor", "ribosome",
          "central dogma"], False),
        ("Genetics", "Chromosomal Genetics",
         ["chromosome", "karyotype", "diploid", "haploid", "meiosis", "mitosis",
          "crossing over", "chromosomal aberration", "linkage", "sex determination",
          "sex linked", "mutation", "mutagenic"], False),
        ("Genetics", "Mendelian Genetics",
         ["mendel", "allele", "dominant", "recessive", "genotype", "phenotype",
          "homozygous", "heterozygous", "punnett square", "test cross",
          "monohybrid", "dihybrid", "law of segregation", "independent assortment",
          "incomplete dominance", "codominance", "multiple allele", "blood group"], False),

        # Plant Biology 
        ("Plant Physiology", "Photosynthesis",
         ["photosynthesis", "chlorophyll", "light reaction", "dark reaction",
          "calvin cycle", "c3 plant", "c4 plant", "cam plant", "photorespiration",
          "photosystem", "electron transport chain plant", "atp synthase chloroplast",
          "chemiosmosis", "rubisco"], False),
        ("Plant Physiology", "Plant Growth",
         ["auxin", "gibberellin", "cytokinin", "ethylene plant", "abscisic acid",
          "phytochrome", "vernalization", "photoperiodism", "dormancy",
          "germination", "apical dominance", "tropism"], False),
        ("Plant Physiology", "Transport in Plants",
         ["transpiration", "stomata", "xylem", "phloem", "translocation",
          "ascent of sap", "root pressure", "osmosis plant", "water potential",
          "mineral absorption", "active transport plant"], False),
        ("Plant Physiology", "Plant Respiration",
         ["glycolysis", "krebs cycle", "oxidative phosphorylation", "fermentation",
          "anaerobic respiration", "aerobic respiration", "respiratory quotient",
          "substrate level phosphorylation"], False),
        ("Plant Kingdom", "Plant Classification",
         ["algae", "bryophyte", "pteridophyte", "gymnosperm", "angiosperm",
          "monocot", "dicot", "thallophyte", "tracheophyte", "cryptogam",
          "phanerogam", "plant kingdom classification"], False),

        # Animal & Human Biology
        ("Human Physiology", "Neural & Chemical Coordination",
         ["neuron", "synapse", "neurotransmitter", "action potential",
          "depolarization", "repolarization", "resting potential",
          "central nervous system", "peripheral nervous", "reflex arc",
          "hormone", "endocrine gland", "hypothalamus", "pituitary",
          "thyroid", "adrenal", "insulin", "glucagon", "feedback mechanism"], False),
        ("Human Physiology", "Excretion",
         ["kidney", "nephron", "urine formation", "glomerular filtration",
          "tubular reabsorption", "tubular secretion", "osmoregulation",
          "urea cycle", "creatinine", "dialysis", "bowman capsule",
          "loop of henle", "collecting duct"], False),
        ("Human Physiology", "Locomotion & Movement",
         ["muscle", "sarcomere", "myosin", "actin", "muscle contraction",
          "sliding filament", "bone", "joint", "skeleton", "lever",
          "synovial joint", "cartilage", "ligament", "tendon"], False),
        ("Human Physiology", "Circulation",
         ["heart", "blood vessel", "artery", "vein", "capillary",
          "cardiac cycle", "ecg", "blood pressure", "pulse",
          "lymph", "erythrocyte", "leucocyte", "platelet", "haemoglobin",
          "blood group", "clotting", "coronary"], False),
        ("Human Physiology", "Breathing",
         ["lung", "breathing", "respiration", "alveolus", "tidal volume",
          "vital capacity", "inspiration", "expiration", "respiratory center",
          "oxygen transport", "carbon dioxide transport", "haemoglobin"], False),
        ("Human Physiology", "Digestion",
         ["digestion", "stomach", "intestine", "liver", "pancreas",
          "enzyme digestion", "bile", "peristalsis", "absorption",
          "villi", "microvilli", "alimentary canal", "salivary amylase"], False),
        ("Animal Kingdom", "Animal Classification",
         ["porifera", "coelenterate", "platyhelminthes", "nematode", "annelida",
          "arthropoda", "mollusca", "echinodermata", "chordata", "vertebrate",
          "invertebrate", "symmetry", "coelom", "notochord", "classification animal"], False),

        # Reproduction 
        ("Reproduction", "Human Reproduction",
         ["testis", "ovary", "spermatogenesis", "oogenesis", "fertilization human",
          "implantation", "pregnancy", "placenta", "parturition",
          "menstrual cycle", "ovulation", "contraception", "ivf"], False),
        ("Reproduction", "Plant Reproduction",
         ["pollination", "pollen", "seed", "fruit", "flower", "stamen", "pistil",
          "ovule", "double fertilization", "endosperm", "embryo plant",
          "vegetative propagation", "apomixis"], False),
        ("Reproduction", "Reproduction",
         ["reproduction", "sexual reproduction", "asexual reproduction",
          "fission", "budding", "fragmentation", "regeneration",
          "gamete", "zygote", "embryo"], False),

        # Ecology 
        ("Ecology", "Biodiversity & Conservation",
         ["biodiversity", "species richness", "endemic species", "extinction",
          "red list", "iucn", "hotspot", "protected area", "wildlife reserve",
          "in-situ", "ex-situ", "conservation"], False),
        ("Ecology", "Environmental Issues",
         ["deforestation", "reforestation", "desertification", "soil erosion",
          "acid rain", "greenhouse gas", "global warming", "climate change",
          "ozone depletion", "water pollution", "air pollution"], False),
        ("Ecology", "Ecosystem",
         ["ecosystem", "food chain", "food web", "trophic level", "energy flow",
          "nutrient cycle", "carbon cycle", "nitrogen cycle", "water cycle",
          "producer", "consumer", "decomposer", "primary productivity",
          "ecological pyramid", "biomass"], False),
        ("Ecology", "Population Ecology",
         ["population", "community", "habitat", "niche", "competition",
          "predation", "symbiosis", "mutualism", "commensalism", "parasitism",
          "succession", "climax community", "carrying capacity", "growth rate"], False),

        # Evolution
        ("Evolution", "Evolution",
         ["evolution", "natural selection", "darwin", "lamarck", "adaptation",
          "fossil", "homologous organ", "analogous organ", "vestigial",
          "hardy-weinberg", "genetic drift", "gene flow", "speciation",
          "reproductive isolation"], False),

        # Cell Biology 
        ("Cell Biology", "Cell Division",
         ["mitosis", "meiosis", "prophase", "metaphase", "anaphase", "telophase",
          "spindle fiber", "centromere", "kinetochore", "cytokinesis",
          "interphase", "g1 phase", "s phase", "g2 phase"], False),
        ("Cell Biology", "Biomolecules",
         ["protein", "amino acid", "polypeptide", "enzyme kinetics",
          "km value", "substrate", "enzyme inhibition", "competitive inhibition",
          "lipid", "phospholipid", "steroid", "fatty acid", "nucleic acid",
          "atp", "nadh", "fadh2", "coenzyme"], False),
        ("Cell Biology", "Cell Structure",
         ["cell wall", "cell membrane", "plasma membrane", "nucleus", "mitochondria",
          "chloroplast", "ribosome", "golgi", "endoplasmic reticulum",
          "lysosome", "vacuole", "centriole", "cytoskeleton", "prokaryotic",
          "eukaryotic", "organelle", "cytoplasm"], False),
    ],
}

# TOPIC CLASSIFIER
def classify_topic(text: str, subject: str) -> tuple[str, str]:
    if subject not in TAXONOMY:
        return "General", "General"

    text_lower = text.lower()
    entries = TAXONOMY[subject]

    for topic, subtopic, keywords, is_regex in entries:
        if is_regex:
            # Regex match — compile each pattern separately for safety
            for pattern in keywords:
                try:
                    if re.search(pattern, text):
                        return topic, subtopic
                except re.error:
                    continue
        else:
            # Plain substring match on lowercased text
            for kw in keywords:
                if kw in text_lower:
                    return topic, subtopic

    return "General", "General"

# BATCH PROCESSING
def extract_topics_batch(df: pd.DataFrame) -> pd.DataFrame:
    logger.info(f"Extracting topics from {len(df):,} questions...")
    topics = []
    subtopics = []
    total = len(df)
    log_every = 10_000

    for i, row in enumerate(df.itertuples(index=False)):
        if i % log_every == 0 and i > 0:
            pct = i / total * 100
            logger.info(f"  Progress: {i:>7,} / {total:,}  ({pct:.1f}%)")

        topic, subtopic = classify_topic(row.eng, row.Subject)
        topics.append(topic)
        subtopics.append(subtopic)

    logger.info(f"  Progress: {total:,} / {total:,}  (100.0%) — Extraction complete")

    df = df.copy()
    df["topic"]    = topics
    df["subtopic"] = subtopics

    return df

# PATH RESOLUTION
def resolve_paths(input_csv: str) -> dict:
    script_dir = Path(__file__).parent
    paths = {
        "input":  Path(input_csv) if os.path.isabs(input_csv)
                  else script_dir / input_csv,
        "output": script_dir / "data" / "processed" / "topics_extracted.csv",
        "report": script_dir / "data" / "reports" / "topic_report.json",
    }
    paths["output"].parent.mkdir(parents=True, exist_ok=True)
    paths["report"].parent.mkdir(parents=True, exist_ok=True)
    return paths



# REPORT GENERATION
def generate_report(df: pd.DataFrame, paths: dict, start_time: datetime) -> dict:
    """Generate full coverage and distribution audit report."""
    duration = (datetime.now() - start_time).total_seconds()

    per_subject = {}
    for subject in df["Subject"].unique():
        subdf = df[df["Subject"] == subject]
        total = len(subdf)

        general_count = (subdf["topic"] == "General").sum()
        coverage = round((total - general_count) / total * 100, 2)

        topic_dist = subdf["topic"].value_counts().to_dict()
        subtopic_dist = subdf["subtopic"].value_counts().head(20).to_dict()

        per_subject[subject] = {
            "total":             total,
            "matched":           total - int(general_count),
            "general_fallback":  int(general_count),
            "coverage_pct":      coverage,
            "topic_distribution":   {k: int(v) for k, v in topic_dist.items()},
            "top_subtopics":        {k: int(v) for k, v in subtopic_dist.items()},
        }

    global_general = (df["topic"] == "General").sum()
    global_coverage = round((len(df) - global_general) / len(df) * 100, 2)

    report = {
        "pipeline_step": "03_extract_topics.py",
        "timestamp":     datetime.now().isoformat(),
        "duration_seconds": round(duration, 2),
        "global_summary": {
            "total_rows":       len(df),
            "matched_rows":     len(df) - int(global_general),
            "general_fallback": int(global_general),
            "global_coverage_pct": global_coverage,
        },
        "per_subject_analysis": per_subject,
        "output_path": str(paths["output"]),
    }

    with open(paths["report"], "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Topic report saved: {paths['report']}")
    return report



# PIPELINE ORCHESTRATOR
def run_topic_pipeline(input_csv: str) -> dict:
    start_time = datetime.now()
    logger.info("=" * 65)
    logger.info("03_extract_topics.py — Starting Topic Extraction Pipeline")
    logger.info("=" * 65)

    paths = resolve_paths(input_csv)

    # Load
    logger.info(f"Loading: {paths['input']}")
    df = pd.read_csv(paths["input"])
    logger.info(f"Loaded {len(df):,} rows with columns: {df.columns.tolist()}")

    # Validate
    required = {"row_id", "eng", "Subject", "difficulty_level", "difficulty_score"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Extract
    df = extract_topics_batch(df)

    # Save — preserve all upstream columns plus new topic/subtopic
    output_cols = [
        "row_id", "eng", "Subject",
        "difficulty_level", "difficulty_score", "estimated_time",
        "question_type", "has_latex", "raw_formula_count", "raw_symbol_count",
        "score_length", "score_formula", "score_symbol", "score_type", "score_keyword",
        "topic", "subtopic",
    ]
    df[output_cols].to_csv(paths["output"], index=False, encoding="utf-8")
    logger.info(f"Output saved: {len(df):,} rows → {paths['output']}")

    # Report
    report = generate_report(df, paths, start_time)

    # Summary console output
    duration = (datetime.now() - start_time).total_seconds()
    logger.info("=" * 65)
    logger.info("TOPIC EXTRACTION COMPLETE — SUMMARY")
    logger.info("=" * 65)
    logger.info(f"  Total rows:        {len(df):,}")
    logger.info(f"  Global coverage:   {report['global_summary']['global_coverage_pct']}%")
    logger.info(f"  General fallback:  {report['global_summary']['general_fallback']:,}")
    logger.info(f"  Duration:          {duration:.1f}s")
    logger.info("")
    logger.info("  PER-SUBJECT COVERAGE:")
    for subject, data in report["per_subject_analysis"].items():
        logger.info(
            f"    {subject:<12}: {data['coverage_pct']:>5.1f}% matched  "
            f"({data['general_fallback']:>5,} General fallback)"
        )
    logger.info("=" * 65)
    logger.info("Next step: Run 04_generate_embeddings.py")
    logger.info("=" * 65)

    return report


# ENTRY POINT
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Step 3: Extract topic and subtopic for all questions"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="data/processed/difficulty_scored.csv",
        help="Path to difficulty_scored.csv"
    )
    args = parser.parse_args()

    report = run_topic_pipeline(args.input)

    # Verification printout
    print("\n" + "=" * 65)
    print("QUICK VERIFICATION — TOPIC COVERAGE")
    print("=" * 65)
    print(f"Global coverage: {report['global_summary']['global_coverage_pct']}%")
    print(f"General fallback: {report['global_summary']['general_fallback']:,} rows")
    print()
    for subject, data in report["per_subject_analysis"].items():
        print(f"\n{subject} ({data['coverage_pct']}% matched):")
        for topic, count in sorted(data["topic_distribution"].items(),
                                   key=lambda x: -x[1])[:8]:
            pct = count / data["total"] * 100
            print(f"  {topic:<35}: {count:>6,}  ({pct:.1f}%)")