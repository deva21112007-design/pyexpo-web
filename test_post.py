import requests

session = requests.Session()
# Register test user
session.post("http://localhost:5000/register", data={"username": "tester", "password": "password"})
# Submit feedback
response = session.post("http://localhost:5000/community-reviews", data={
    "name": "Local Tester",
    "email": "test@example.com",
    "rating": "5",
    "message": "Testing 500 error locally"
})
print("Status Code:", response.status_code)
if response.status_code == 500:
    print("Received 500 Error!")
    print(response.text[:1000])
else:
    print("Success or rendered error message:")
    # Look for error or success string in HTML
    if "Error saving feedback" in response.text:
        print("Found 'Error saving feedback' in HTML.")
    elif "Thank you for your feedback!" in response.text:
        print("Found 'Thank you for your feedback!' in HTML.")
    else:
        print("Unexpected HTML content.")
