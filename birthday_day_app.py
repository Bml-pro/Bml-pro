# filename: birthday_explorer_dynamic.py

import streamlit as st
import datetime
import random

st.set_page_config(page_title="Birthday Explorer", page_icon="🎉", layout="wide")

st.title("🎂 Birthday Explorer")
st.markdown("""
Discover the day you were born and explore a fun fact from your birth year!
""")

# --- User Input ---
col1, col2, col3 = st.columns(3)

with col1:
    year = st.number_input(
        "Year", 
        min_value=1000, 
        max_value=datetime.date.today().year, 
        value=2000, 
        step=1
    )

with col2:
    month = st.selectbox(
        "Month", 
        list(range(1, 13)), 
        format_func=lambda x: datetime.date(1900, x, 1).strftime('%B')
    )

with col3:
    # Adjust day max based on month & year
    max_day = (datetime.date(year + int(month/12), (month % 12) + 1, 1) - datetime.timedelta(days=1)).day
    day = st.number_input("Day", min_value=1, max_value=max_day, value=1, step=1)

# --- Calculate Birthday ---
if st.button("Explore Birthday"):
    try:
        birthdate = datetime.date(year, month, day)
        day_of_week = birthdate.strftime("%A")
        
        # Emoji for day
        day_emojis = {
            "Monday": "🌞",
            "Tuesday": "🌮",
            "Wednesday": "🐪",
            "Thursday": "⚡",
            "Friday": "🎉",
            "Saturday": "🏖️",
            "Sunday": "🛌"
        }
        emoji = day_emojis.get(day_of_week, "")
        
        # Specific historical facts
        facts_specific = {
            1453: "1453 – Fall of Constantinople marked the end of the Byzantine Empire!",
            1492: "1492 – Columbus discovered America! 🌎",
            1776: "1776 – USA Declaration of Independence 🇺🇸",
            1969: "1969 – Humans landed on the Moon! 🚀",
            2000: "2000 – The world celebrated the new millennium! 🎆",
            2020: "2020 – Global pandemic changed the world 🦠",
        }
        
        # Generic fun facts pool
        facts_generic = [
            "A very special year in history! 🎈",
            "This year saw many exciting events around the world! 🌍",
            "An unforgettable year for humanity! 🌟",
            "A year full of surprises and milestones! 🏆",
            "History remembers many interesting things about this year! 📜",
        ]
        
        # Choose fact
        year_fact = facts_specific.get(year, random.choice(facts_generic))
        
        # Display results
        st.success(f"You were born on a **{day_of_week} {emoji}**!")
        st.info(year_fact)
        
    except Exception as e:
        st.error(f"Error: {e}")

