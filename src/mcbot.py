import asyncio
import os
import json
from nio import AsyncClient, RoomVisibility
from nio.responses import LoginResponse, RoomSendResponse, RoomSendError


def load_state(path='./config/state.json'):
    """Load JSON state from `path`. Returns a dict (empty on error)."""
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f) or {}
    except Exception as e:
        print(f"Failed to read state file {path}: {type(e).__name__}: {e}")
    return {}


def save_state(state: dict, path='./config/state.json'):
    """Save `state` dict to `path`, creating parent directories if needed."""
    try:
        parent = os.path.dirname(path) or '.'
        os.makedirs(parent, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Failed to write state file {path}: {type(e).__name__}: {e}")
        raise


def update_state(updates: dict, path='./config/state.json'):
    """Merge `updates` into existing state and persist to disk."""
    state = load_state(path)
    state.update(updates)
    save_state(state, path)
    return state

def load_config(path='bot.conf'):
    """Load configuration from JSON `bot.conf` with sensible defaults."""
    cfg = {}
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                cfg = json.load(f) or {}
    except Exception as e:
        print(f"Warning: failed to read config {path}: {type(e).__name__}: {e}")
    return cfg


async def main():
    # Load configuration
    cfg = load_config()
    homeserver = cfg['matrix_homeserver']
    user_id = cfg['matrix_user_id']
    password = cfg['matrix_password']

    client = AsyncClient(homeserver, user_id)
    
    try:
        # Check for password presence
        if not password or password == "your_matrix_password_here":
            print("Error: Matrix password not found in bot.conf.")
            await client.close()
            return

        # Attempt login
        login_response = await client.login(password)
        
        # Check if login was successful
        if not isinstance(login_response, LoginResponse):
            print(f"Login failed: {login_response}")
            await client.close()
            return
        
        print(f"Login successful: {login_response.user_id}")

        # List joined rooms so you can pick the correct `room_id`
        # await list_rooms(client)

        # Send a direct message to a specific user
        target_user = cfg['target_user']
        try:
            # Try to use saved dm_room_id from state
            sent = False
            state = load_state()
            saved_room = state.get('dm_room_id')

            if saved_room:
                room_id = saved_room
                try:
                    message_response = await client.room_send(
                        room_id=room_id,
                        message_type="m.room.message",
                        content={"msgtype": "m.text", "body": "Hello from McBot!"}
                    )

                    if isinstance(message_response, RoomSendResponse):
                        print(f"Direct message sent using saved room {room_id} with event ID: {message_response.event_id}")
                        sent = True
                    else:
                        print(f"Failed to send DM using saved room {room_id}: {message_response} — will create a new room")
                except Exception as e:
                    print(f"Failed to send to saved DM {room_id}: {type(e).__name__}: {e} — will create a new room")

            if not sent:
                # Create (or invite) a direct chat with the user
                create_resp = await client.room_create(
                    invite=[target_user], 
                    is_direct=True,
                    visibility=RoomVisibility.private,
                    name="McBot-DM")
                room_id = getattr(create_resp, "room_id", None)

                if not room_id:
                    print(f"Failed to create direct room: {create_resp}")
                else:
                    try:
                        update_state({'dm_room_id': room_id})
                        print("Stored DM room_id in ./config/state.json")
                    except Exception as e:
                        print(f"Failed to update state: {type(e).__name__}: {e}")

                    message_response = await client.room_send(
                        room_id=room_id,
                        message_type="m.room.message",
                        content={"msgtype": "m.text", "body": "Hello World"}
                    )

                    # Check if message was sent successfully
                    if not isinstance(message_response, RoomSendResponse):
                        print(f"Failed to send DM: {message_response}")
                    else:
                        print(f"Direct message sent successfully with event ID: {message_response.event_id}")

        except asyncio.TimeoutError:
            print("Error: Direct message sending timed out")
        except RoomSendError as e:
            print(f"Failed to send DM: {type(e).__name__}: {e}")
            if "M_FORBIDDEN" in str(e):
                try:
                    pl_resp = await client.room_get_state_event(room_id, "m.room.power_levels", "")
                    content = getattr(pl_resp, "content", None) or pl_resp
                    if isinstance(content, dict):
                        users = content.get("users", {})
                        user_key = getattr(login_response, "user_id", None) or getattr(client, "user_id", None)
                        user_level = users.get(user_key, content.get("users_default", 0))
                        events = content.get("events", {})
                        send_level = events.get("m.room.message", content.get("events_default", 0))
                        print(f"Permission denied: your power level is {user_level}, required for sending m.room.message is {send_level}.")
                        print("Possible fixes: ask a room admin to lower the required send level or raise the bot's power level, or use a room where the bot has send permission.")
                    else:
                        print("Could not retrieve power levels for the room.")
                except Exception as e2:
                    print(f"Failed to fetch power levels: {type(e2).__name__}: {e2}")
        except Exception as e:
            print(f"Error sending DM: {type(e).__name__}: {e}")
    
    except asyncio.TimeoutError:
        print("Error: Login request timed out")
    except Exception as e:
        print(f"Login failed with error: {type(e).__name__}: {e}")
    
    finally:
        await client.close()

asyncio.run(main())