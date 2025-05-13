import streamlit as st
import datetime
import time
import uuid
import json
import os
import html

REMINDERS_FILE = "reminders_data.json"

STATUS_PENDING = "pending"
STATUS_DUE = "due"
STATUS_DISMISSED = "dismissed"
STATUS_COMPLETED = "completed"

def calculate_due_time(value, unit):
    """Calculates the absolute due time from a relative value and unit."""
    now = datetime.datetime.now()
    if unit == "seconds":
        return now + datetime.timedelta(seconds=value)
    elif unit == "minutes":
        return now + datetime.timedelta(minutes=value)
    elif unit == "hours":
        return now + datetime.timedelta(hours=value)
    elif unit == "days":
        return now + datetime.timedelta(days=value)
    st.error(f"Unknown time unit: {unit}")
    return now

def format_timedelta_dhms(delta):
    """Formats a timedelta into a string like '2d 3h 5m 10s' or 'Overdue by X'."""
    seconds = delta.total_seconds()
    
    if seconds <= 0:
        abs_seconds = abs(seconds)
        days, rem = divmod(abs_seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)
        
        parts = []
        if days > 0: parts.append(f"{int(days)}d")
        if hours > 0: parts.append(f"{int(hours)}h")
        if minutes > 0: parts.append(f"{int(minutes)}m")
        if secs > 0 or not parts: parts.append(f"{int(secs)}s")
        
        return f"Overdue by {' '.join(parts) if parts else '0s'}!" if abs_seconds > 0 else "Due NOW!"

    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts = []
    if days > 0: parts.append(f"{int(days)}d")
    if hours > 0: parts.append(f"{int(hours)}h")
    if minutes > 0: parts.append(f"{int(minutes)}m")
    if not parts or (days == 0 and hours == 0 and minutes == 0):
        parts.append(f"{int(secs)}s")
    
    return " ".join(parts)

def save_reminders_to_file(reminders_list):
    """Saves the list of reminders to a JSON file."""

    serializable_reminders = []
    for r in reminders_list:
        sr = r.copy()
        sr['due_time'] = sr['due_time'].isoformat() if isinstance(sr.get('due_time'), datetime.datetime) else sr.get('due_time')
        sr['created_at'] = sr['created_at'].isoformat() if isinstance(sr.get('created_at'), datetime.datetime) else sr.get('created_at')
        if sr.get('completed_at') and isinstance(sr.get('completed_at'), datetime.datetime):
            sr['completed_at'] = sr['completed_at'].isoformat()
        serializable_reminders.append(sr)
    
    try:
        with open(REMINDERS_FILE, 'w') as f:
            json.dump(serializable_reminders, f, indent=4)
    except IOError as e:
        st.error(f"Error saving reminders: {e}")

def load_reminders_from_file():
    """Loads reminders from a JSON file."""
    if not os.path.exists(REMINDERS_FILE):
        return []
    try:
        with open(REMINDERS_FILE, 'r') as f:
            loaded_reminders = json.load(f)
        
            deserialized_reminders = []
            for r in loaded_reminders:
                lr = r.copy()
                lr['due_time'] = datetime.datetime.fromisoformat(r['due_time']) if isinstance(r.get('due_time'), str) else r.get('due_time')
                lr['created_at'] = datetime.datetime.fromisoformat(r['created_at']) if isinstance(r.get('created_at'), str) else r.get('created_at')
                if r.get('completed_at') and isinstance(r.get('completed_at'), str):
                    lr['completed_at'] = datetime.datetime.fromisoformat(r['completed_at'])
                deserialized_reminders.append(lr)
            return deserialized_reminders
    except (IOError, json.JSONDecodeError) as e:
        st.error(f"Error loading reminders: {e}. Starting with an empty list.")
        return []

st.set_page_config(page_title="Reminder App", layout="centered")
st.title("⏳ Reminder App")

if 'reminders' not in st.session_state or not st.session_state.get('data_loaded_from_file', False):
    st.session_state.reminders = load_reminders_from_file()
    st.session_state.data_loaded_from_file = True

st.header("🔔 Add New Reminder")
with st.form("reminder_form", clear_on_submit=True):
    task_description = st.text_input("Task Description:", placeholder="e.g., Buy groceries")
    
    col1, col2 = st.columns([1,1])
    with col1:
        time_value = st.number_input("Remind me in:", min_value=1, value=10, step=1)
    with col2:
        time_unit = st.selectbox("Unit:", ["seconds", "minutes", "hours", "days"], index=1)
    
    submitted = st.form_submit_button("Add Reminder")

if submitted and task_description:
    due_time = calculate_due_time(time_value, time_unit)
    new_reminder = {
        "id": str(uuid.uuid4()),
        "task": task_description,
        "due_time": due_time,
        "created_at": datetime.datetime.now(),
        "status": STATUS_PENDING,
        "completed_at": None
    }
    st.session_state.reminders.append(new_reminder)
    save_reminders_to_file(st.session_state.reminders)
    st.success(f"Reminder for '{html.escape(task_description)}' set for {due_time.strftime('%Y-%m-%d %H:%M:%S')}.")
    st.rerun()

st.header("📝 Your Reminders")

if not st.session_state.reminders:
    st.info("No reminders yet. Add one above!")
else:
    current_time = datetime.datetime.now()
    due_notifications_this_cycle = []


    pending_due_reminders = []
    completed_reminders_list = []

    for r in st.session_state.reminders:
        if r['status'] == STATUS_DISMISSED:
            continue
        if r['status'] == STATUS_COMPLETED:
            completed_reminders_list.append(r)
        else:
            pending_due_reminders.append(r)
    

    sorted_active_reminders = sorted(pending_due_reminders, key=lambda r: r['due_time'])
    sorted_completed_reminders = sorted(completed_reminders_list, key=lambda r: r.get('completed_at') or r['created_at'], reverse=True)


    if sorted_active_reminders:
        st.subheader("Active")
        for reminder in sorted_active_reminders:
            time_left = reminder['due_time'] - current_time
            task_id = reminder['id']
            escaped_task = html.escape(reminder['task'])

        
            if time_left.total_seconds() <= 0 and reminder['status'] == STATUS_PENDING:
                reminder['status'] = STATUS_DUE
                due_notifications_this_cycle.append(reminder['task'])
            
                save_reminders_to_file(st.session_state.reminders)


            status_color = "grey"
            time_display = ""
            text_style = ""

            if reminder['status'] == STATUS_DUE:
                status_icon = "🚨"
                status_color = "red"
                time_display = f"**{format_timedelta_dhms(time_left)}** (Originally: {reminder['due_time'].strftime('%H:%M:%S')})"
            elif reminder['status'] == STATUS_PENDING:
                status_icon = "⏳"
                status_color = "blue"
                time_display = f"Due in: {format_timedelta_dhms(time_left)} (at {reminder['due_time'].strftime('%H:%M:%S')})"
            
        
        
        
            is_completed_by_user = st.checkbox(
                f"Mark as completed: '{escaped_task[:20]}...'", 
                value=(reminder['status'] == STATUS_COMPLETED), 
                key=f"complete_{task_id}"
            )

            if is_completed_by_user and reminder['status'] != STATUS_COMPLETED:
                reminder['status'] = STATUS_COMPLETED
                reminder['completed_at'] = datetime.datetime.now()
                save_reminders_to_file(st.session_state.reminders)
                st.toast(f"Completed: {escaped_task}", icon="👍")
                st.rerun()
            
            st.markdown(f"""
            <div style="border: 1px solid {status_color}; border-left: 5px solid {status_color}; padding: 10px; border-radius: 5px; margin-bottom: 5px; {text_style}">
                <strong>{status_icon} {escaped_task}</strong><br>
                <small>{time_display}</small>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Dismiss '{escaped_task[:15]}...'", key=f"dismiss_{task_id}"):
                reminder['status'] = STATUS_DISMISSED
                save_reminders_to_file(st.session_state.reminders)
                st.toast(f"Dismissed: {escaped_task}", icon="🗑️")
                st.rerun()
            st.markdown("---")
    else:
        st.info("No active reminders.")
        


    if sorted_completed_reminders:
        st.subheader("Completed")
        for reminder in sorted_completed_reminders:
            task_id = reminder['id']
            escaped_task = html.escape(reminder['task'])
            status_icon = "✅"
            status_color = "green"
            text_style = "text-decoration: line-through; opacity: 0.7;"
            completed_time_str = f"Completed on: {reminder['completed_at'].strftime('%Y-%m-%d %H:%M')}" if reminder.get('completed_at') else "Completed"

        
            is_still_completed = st.checkbox(
                f"Completed: '{escaped_task[:20]}...'", 
                value=True,
                key=f"uncomplete_{task_id}"
            )

            if not is_still_completed:
                reminder['status'] = STATUS_PENDING
                reminder['completed_at'] = None
                save_reminders_to_file(st.session_state.reminders)
                st.toast(f"Reactivated: {escaped_task}", icon="🔄")
                st.rerun()

            st.markdown(f"""
            <div style="border: 1px solid {status_color}; border-left: 5px solid {status_color}; padding: 10px; border-radius: 5px; margin-bottom: 5px; {text_style}">
                <strong>{status_icon} {escaped_task}</strong><br>
                <small>{completed_time_str}</small>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"Dismiss '{escaped_task[:15]}...'", key=f"dismiss_completed_{task_id}"):
                reminder['status'] = STATUS_DISMISSED
                save_reminders_to_file(st.session_state.reminders)
                st.toast(f"Dismissed: {escaped_task}", icon="🗑️")
                st.rerun()
            st.markdown("---")



    for task_name in due_notifications_this_cycle:
        st.toast(f"Reminder: '{html.escape(task_name)}' is due!", icon="⏰")

active_reminders_exist = any(r['status'] in [STATUS_PENDING, STATUS_DUE] for r in st.session_state.reminders)
REFRESH_INTERVAL_SECONDS = 5

if active_reminders_exist:
    time.sleep(REFRESH_INTERVAL_SECONDS)
    st.rerun()
