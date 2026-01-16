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

TCP_QUESTIONS  = {
        "section 1 - values": [
            "What is important to you about money?",
            "What is the role of money in your life?",
            "What in particular is important to you about that value?",
            "Is there anything more important than that value?"
        ],
        "section 2 - goals": [
            "What are your top accomplishments?",
            "What would you like them to be?",
            "What are your professional goals?",
            "What are your personal goals?",
            "What would be the monthly amount to give you the lifestyle you desire?",
            "How much of this amount would you need to cover your essential expenses?",
            "From what age onwards would you like this income stream to start?",
            "What is your healthcare expectation? If you need to be hospitalized, would you like to have the option to go to a private hospital? Do you need to have the option to go overseas for treatment?",
            "Ideally, where would you like to be when you are 45? 55? 65? 75?",
            "If you do not have to work anymore, what would you do?",
            "What do you do (or want to do) for your children?",
            "For tertiary education, which country would you like to provide for them?",
            "If you and/or your spouse is not around, how much would you like to provide for your children on a monthly basis?",
            "If you are down with a severe illness, how many years of income would you like to protect to allow yourself time to recuperate? (3-5years as a guide)",
            "How about a severe disability? How much do you think you would want to provide for your dependents and yourself?",
            "Are your parents still around? Would you need to provide for them? Is there any special thing you would like to do for them?",
            "How about other family members or close friends?",
            "Is there anything you want to do for the world at large? E.g. charities",
            "Do you have any quality-of-life desires – such as houses, travel, boats, cars?",
            "Besides the goals above, is there anything else you want to achieve with your money?",
            "When you think about money, what concerns, needs or feelings come to mind?"
        ],
        "section 3 - relationships": [
            "Which family member relationships (spouse, children, siblings, parents, etc.) are the most important ones to you?",
            "Beside your family, is there any other relationship that is important to you? For example, with friends, at work, community, religion, charity",
            "What is your religious orientation? How devout are you? How important are your relationships with people associated with your religion?",
            "Would you describe yourself as an introvert or an extrovert?",
            "What pets do you have? How important are they to you?",
            "What schools did you go to? How important is your relationship with these schools?"
        ],
        "section 4 - assets": [
            "What is your source of income (privately held business, employer, profession)?",
            "How is that likely to change in the next three years?",
            "How do you save or set aside money to invest? How is that likely to change in the next three years?",
            "What are your investment holdings? Explain your strategy for handling your investments in the way you do.",
            "What benefits do you get from your workplace?",
            "What life insurance do you have?",
            "What property do you have (real property, artwork, jewellery)?",
            "How are your assets structured now?",
            "What new assets do you expect to receive (for example, from inheritances or stock options)?",
            "What is your opinion of taxes? What kinds of taxes bother you the most?",
            "When you think about your finances, what are your three biggest worries?",
            "What were your best and worst financial moves? What happened?"
        ],
        "section 5 - advisors": [
            "Do you have a lawyer? How do you feel about the relationship?",
            "Do you have a life insurance agent? How do you feel about the relationship?",
            "Do you have an accountant? How do you feel about the relationship?",
            "Do you have an investment advisor? How do you feel about the relationship?",
            "Do you have a financial planner? How do you feel about the relationship? How frequently have you switched financial planners?",
            "What were your best and your worst experiences with a professional advisor?"
        ],
        "section 6 - process": [
            "How involved do you like to be in managing your finances?",
            "Do you find managing your finances stressful?",
            "How many face-to-face meetings would you want over the course of a year?",
            "Do you want a call when there is a sudden change in the market?",
            "How often do you want an overall review of your financial situation and progress toward your goals?",
            "Who else do you want involved in the management of your finances (spouse, other advisors such as an accountant or an attorney)?",
            "How important to you is the confidentiality of your financial affairs?"
        ],
        "section 7 - interests": [
            "Do you follow sports? Which are your favourite teams?",
            "What are your favourite types of TV programs and movies?",
            "What do you read?",
            "Do you have health concerns or interests? What is your health program?",
            "Do you exercise regularly? If yes, what type/s of exercise do you do and where do you do them?",
            "What are your hobbies?",
            "What would an ideal weekend be?",
            "What would an ideal vacation be?",
            "What charitable causes do you donate to? Volunteer for?",
            "Who do you most look up to/admire?",
            "Do you have any preferred brands that you always go to? Example: Apple for mobile phones, SIA for flights etc."
        ]
    }


# Categorized questions by template
CATEGORIZED_QUESTIONS = {
    "Pre-discovery": TCP_QUESTIONS,
    "Discovery": TCP_QUESTIONS,
    "POA": TCP_QUESTIONS,
    "Presentation of Plan": TCP_QUESTIONS,
    "Client Onboarding Orientation": TCP_QUESTIONS,
    "Interim Check-in": TCP_QUESTIONS,
    "Wealth Plan Review": TCP_QUESTIONS,
    "General Meeting": TCP_QUESTIONS
}