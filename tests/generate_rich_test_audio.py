import pyttsx3

text = """
Advisor: Good morning, Mr. Howard. Let’s review your planning. Any updates in your lifestyle?
Client: well, not much. My son Lucas is preparing for his college at NUS next year, and my daughter is starting secondary school soon.
Advisor: That’s amazing. How are the weekends?
Client: I'm still trying to cycle at East Coast Park on Saturdays. Also, my wife and I have fully committed to a plant-based diet recently. 
Advisor: Vegan? That’s healthy! Any travel plans?
Client: We are going to Tokyo for two weeks in December. And I am actually thinking about getting a Tesla Model 3 before the trip.
Advisor: Sounds great. Let's look at the numbers.
"""

try:
    engine = pyttsx3.init()
    # Speed and Voice setup for better quality
    engine.setProperty('rate', 150)    
    engine.save_to_file(text, 'rich_client_preference_test.wav')
    engine.runAndWait()
    print("✨ SUCCESS: Created 'rich_client_preference_test.wav' locally !")
except Exception as e:
    print(f"❌ Error during generation: {e}")
