import re

from nemoguardrails.actions import action

INJECTED = re.compile(
    r"ignore (all |any )?(previous|prior) instructions|note to (the )?automated reviewer|"
    r"do not mention this",
    re.IGNORECASE,
)
ACCOUNT = re.compile(r"\b\d{8,17}\b")


@action(name="drop_injected_chunks")
async def drop_injected_chunks(context: dict | None = None) -> str:
    chunks = ((context or {}).get("relevant_chunks") or "").split("\n")
    kept = [c for c in chunks if not INJECTED.search(c)]
    if len(kept) < len(chunks):
        print(
            f"[retrieval rail] quarantined {len(chunks) - len(kept)} chunk(s) for human review"
        )
    return "\n".join(kept)


@action(name="mask_accounts")
async def mask_accounts(text: str) -> str:
    return ACCOUNT.sub(lambda m: "****" + m.group()[-4:], text)
