# Update config/questions.py to add categorized questions

PRESET_QUESTIONS = {
    "tcp": [
        "What is your current occupation?",
        "How many years of work experience do you have?",
        "What are your monthly expenses?",
        "Do you have any existing insurance coverage?",
        "What are your financial goals for the next 5 years?",
        "Do you have any dependents?",
        "What is your annual income?",
        "Do you own any property or real estate?",
        "What is your risk tolerance for investments?",
        "Do you have an emergency fund?",
        "What are your retirement plans?",
        "Do you have any outstanding debts or loans?",
        "Are you currently investing in any financial products?",
        "What is your desired retirement age?",
        "Do you have a will or estate plan in place?",
    ]
}

# Categorized questions by template
CATEGORIZED_QUESTIONS = {
    "tcp": {
        "section 1 - values": [
            "What is important to you about money?",
            "What is the role of money in your life?",
            "What are your core values regarding finances?",
            "How do you define financial success?",
        ],
        "section 2 - goals": [
            "What are your financial goals for the next 5 years?",
            "What are your retirement plans?",
            "What is your desired retirement age?",
            "Do you have a will or estate plan in place?",
            "Do you own any property or real estate?",
        ],
        "section 3 - personal info": [
            "What is your current occupation?",
            "How many years of work experience do you have?",
            "Do you have any dependents?",
            "What is your annual income?",
        ],
        "section 4 - financial status": [
            "What are your monthly expenses?",
            "Do you have any outstanding debts or loans?",
            "Do you have an emergency fund?",
            "What is your risk tolerance for investments?",
        ],
        "section 5 - insurance & investment": [
            "Do you have any existing insurance coverage?",
            "Are you currently investing in any financial products?",
        ],
    }
}