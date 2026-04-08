import requests

session = requests.Session()
session.post("https://pyexpo-web.onrender.com/login", data={"username": "testuser", "password": "testpassword"})

response = session.post("https://pyexpo-web.onrender.com/community-reviews", data={
    "name": "Live Tester",
    "email": "test@example.com",
    "rating": "5",
    "message": "Testing 500 error on live server"
})

print("HTTP Status:", response.status_code)
print("Response Text Snippet:")
print(response.text[:1500])
