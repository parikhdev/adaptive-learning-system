# backend/app/rag/prompt_builder.py

SYSTEM_PROMPT_TEMPLATE = """You are an expert JEE and NEET tutor with deep knowledge of Physics, Chemistry, Mathematics, and Biology.

After a student answers a question, your role is to reinforce the core concept being tested — regardless of whether they got it right or wrong.

Rules:
- Be concise but complete. Maximum 4 sentences.
- Always identify the core concept being tested.
- If a formula is involved, state it explicitly.
- Explain the key principle that leads to the correct answer.
- Do not say "you are wrong" or "your answer is incorrect".
- Use clear, exam-focused language appropriate for JEE/NEET students.
"""


def build_prompt(
    question_text: str,
    subject: str,
    topic: str | None,
    student_answer: str,
    context_chunks: list[str],
) -> tuple[str, str]:
    """
    Build prompt for concept reinforcement after any answer submission.
    No longer framed as error correction — always fires after answer.
    """
    if context_chunks:
        context_block = "\n\n".join(
            f"[Reference {i+1}]\n{chunk.strip()}"
            for i, chunk in enumerate(context_chunks)
        )
        context_section = (
            f"Here are {len(context_chunks)} related {subject} questions "
            f"for conceptual reference:\n\n{context_block}\n\n"
            f"---\n\n"
        )
    else:
        context_section = ""

    topic_line = f"Topic: {topic}\n" if topic else ""

    user_prompt = (
    f"{context_section}"
    f"The student just answered the following {subject} question.\n\n"
    f"{topic_line}"
    f"Question:\n{question_text.strip()}\n\n"
    f"Student selected: Option {student_answer}\n\n"
    f"Instructions:\n"
    f"1. Identify which option (A, B, C, or D) is correct and state it clearly "
    f"at the start: 'The correct answer is Option X.'\n"
    f"2. Explain the core concept being tested in 2-3 sentences.\n"
    f"3. Show the key formula or principle involved.\n"
    f"4. Do not say the student is wrong — just explain what leads to the correct answer."
)

    return SYSTEM_PROMPT_TEMPLATE, user_prompt