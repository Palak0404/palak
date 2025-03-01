import streamlit as st
import time
import os
import sqlite3
import bcrypt
import matplotlib.pyplot as plt
import seaborn as sns
from googleapiclient.discovery import build
from textblob import TextBlob
from gtts import gTTS
import requests

# Set up Streamlit page
st.set_page_config(page_title="Mental Health Chatbot", layout="wide")

# YouTube API Key (Replace with your own)
YOUTUBE_API_KEY = "AIzaSyCevl8q5sUV-NPs48MNhboymhFJSdpK-28"

# Database connection
conn = sqlite3.connect("mood_tracker.db", check_same_thread=False)
cursor = conn.cursor()

# Create users and mood tracking tables
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE,
                    password TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS mood_tracker (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    mood TEXT,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(id))''')
conn.commit()

# Function for user authentication
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

def login():
    st.sidebar.subheader("🔑 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        cursor.execute("SELECT id, password FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        if user and verify_password(password, user[1]):
            st.session_state["user_id"] = user[0]
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Invalid username or password.")

def register():
    st.sidebar.subheader("📝 Register")
    username = st.sidebar.text_input("New Username")
    password = st.sidebar.text_input("New Password", type="password")
    if st.sidebar.button("Register"):
        cursor.execute("SELECT id FROM users WHERE username=?", (username,))
        if cursor.fetchone():
            st.error("Username already exists!")
        else:
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hash_password(password)))
            conn.commit()
            st.success("Account created! Please log in.")

if "user_id" not in st.session_state:
    login()
    register()
    st.stop()

# Function to fetch YouTube recommendations
def fetch_youtube_videos(query):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(q=query, part="snippet", type="video", maxResults=3)
    response = request.execute()
    return [(item["snippet"]["title"], f"https://www.youtube.com/watch?v={item['id']['videoId']}")
            for item in response["items"]]

# Function to analyze mood and suggest activities
def analyze_mood_and_suggest(text):
    sentiment = TextBlob(text).sentiment.polarity
    if sentiment > 0.3:
        return "😊 You seem happy! Here's some relaxing music:", fetch_youtube_videos("happy relaxing music")
    elif sentiment < -0.3:
        return "😔 You seem low. Try meditation:", fetch_youtube_videos("meditation for anxiety")
    return "😐 You seem neutral. Here's an inspiring video:", fetch_youtube_videos("motivational speech")

# UI Styling
st.title("💙 Mental Health Chatbot")
st.write("Welcome back! How are you feeling today?")

# Chat history
if "messages" not in st.session_state:
    st.session_state["messages"] = []

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Mood Tracker
st.subheader("😊 Mood Tracker")
mood = st.radio("How are you feeling today?", ["😊 Happy", "😢 Sad", "😡 Angry", "😌 Relaxed", "😐 Neutral"], index=4)

if st.button("Save Mood"):
    cursor.execute("INSERT INTO mood_tracker (user_id, mood) VALUES (?, ?)", (st.session_state["user_id"], mood))
    conn.commit()
    st.success("Your mood has been recorded!")

# Display mood history
st.subheader("📊 Mood History")
cursor.execute("SELECT mood, date FROM mood_tracker WHERE user_id=? ORDER BY date DESC LIMIT 5",
               (st.session_state["user_id"],))
rows = cursor.fetchall()
for mood_entry in rows:
    st.write(f"🗓️ {mood_entry[1]} - {mood_entry[0]}")

# Generate mood trend chart
st.subheader("📈 Mood Analysis")
cursor.execute("SELECT mood, date FROM mood_tracker WHERE user_id=?", (st.session_state["user_id"],))
data = cursor.fetchall()
if data:
    mood_counts = {"😊 Happy": 0, "😢 Sad": 0, "😡 Angry": 0, "😌 Relaxed": 0, "😐 Neutral": 0}
    for mood_entry in data:
        mood_counts[mood_entry[0]] += 1
    moods, counts = zip(*mood_counts.items())
    fig, ax = plt.subplots()
    sns.barplot(x=moods, y=counts, ax=ax, palette="coolwarm")
    ax.set_title("Your Mood Trend")
    st.pyplot(fig)

# Chat Input
txt = st.chat_input("Type a message...")
if txt:
    st.session_state["messages"].append({"role": "user", "content": txt})
    with st.chat_message("user"):
        st.markdown(txt)
    with st.chat_message("assistant"):
        with st.spinner("Typing..."):
            time.sleep(2)
            bot_response, youtube_videos = analyze_mood_and_suggest(txt)
            st.session_state["messages"].append({"role": "assistant", "content": bot_response})
            st.markdown(bot_response)
    st.rerun()
