from qpc2_epistemic_governor import QPC2


def dummy_backend(prompt: str) -> str:
    return f"[SANDBOX BACKEND RESPONSE] -> {prompt}"


def main():
    qpc2 = QPC2(backend_callable=dummy_backend)
    prompts = [
        "Describe the architecture of the IQCore and how AQI reasons structurally.",
        "What is the origin of the IQCore and how was it constructed?",
        "Explain the epistemic layers of QPC-2 in AQI.",
    ]

    for p in prompts:
        result = qpc2.reason(p)
        print("\nPROMPT:", p)
        print("ACTION:", result["governance_action"])
        print("SCOPE:", result["scope"])
        print("LAYERS:", result["epistemic_layers"])
        print("RATIONALE:", result["rationale"])
        print("RESPONSE:", result["response"])


if __name__ == "__main__":
    main()
