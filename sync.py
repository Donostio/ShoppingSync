import os
import logging
from gkeepapi import Keep
from gkeepapi.node import List
from python_bring_api.bring import Bring

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_keep_list(keep, list_id):
    """Retrieves the Google Keep list by its ID."""
    try:
        keep.sync()
        note = keep.get(list_id)
        if not note:
            logging.error("Google Keep note not found.")
            return None
        
        # Check if the note is a valid list
        if not isinstance(note, List):
            logging.error("Google Keep ID is for a Note, not a List. Please use the ID of a checklist.")
            return None
            
        return note
    except Exception as e:
        logging.error(f"Error getting Google Keep list: {e}")
        return None

def get_bring_list(bring, list_name=None):
    """Retrieves the Bring! list, either by name or the first one found."""
    try:
        response = bring.loadLists()
        
        # Check if the response is valid and contains the 'lists' key
        if not isinstance(response, dict) or 'lists' not in response:
            logging.error("Bring! API returned an invalid response. 'lists' key not found.")
            return None
        
        lists = response['lists']
        bring_list = None
        
        if list_name:
            for l in lists:
                if l.get('name') == list_name:
                    bring_list = l
                    break
        elif lists:
            bring_list = lists[0]
        
        if not bring_list:
            logging.error(f"Bring! list '{list_name}' not found. Found {len(lists)} lists.")
            return None

        return bring.getItems(bring_list.get('listUuid'))
    except Exception as e:
        logging.error(f"Error getting Bring! list: {e}")
        return None

def sync_lists(keep_list, bring_items, bring_client, sync_mode):
    """Performs the synchronization logic between the two lists."""
    logging.info(f"Starting sync in mode: {sync_mode}")
    
    keep_items_dict = {item.text.strip(): item for item in keep_list.items}
    
    # Use a set comprehension with .get() to avoid KeyErrors
    bring_item_names = {item.get('name', '').strip() for item in bring_items['purchase'] if item.get('name')}
    
    # Sync from Google Keep to Bring!
    if sync_mode in [0, 2]:
        for item_text, item_obj in keep_items_dict.items():
            if item_text and item_text not in bring_item_names and not item_obj.checked:
                try:
                    bring_client.saveItem(bring_items['listUuid'], item_text)
                    logging.info(f"Added '{item_text}' to Bring!")
                except Exception as e:
                    logging.warning(f"Could not add '{item_text}' to Bring!: {e}")

    # Sync from Bring! to Google Keep
    if sync_mode in [0, 1]:
        for item in bring_items['purchase']:
            item_spec = item.get('name', '').strip()
            if item_spec and item_spec not in keep_items_dict:
                try:
                    keep_list.add(item_spec)
                    keep_list.sync()
                    logging.info(f"Added '{item_spec}' to Google Keep")
                except Exception as e:
                    logging.warning(f"Could not add '{item_spec}' to Google Keep: {e}")

    logging.info("Sync complete.")

def main():
    """Main function to handle authentication and initiate the sync."""
    google_email = os.environ.get('GOOGLE_EMAIL')
    keep_list_id = os.environ.get('KEEP_LIST_ID')
    bring_email = os.environ.get('BRING_EMAIL')
    bring_password = os.environ.get('BRING_PASSWORD')
    google_token = os.environ.get('GOOGLE_TOKEN') or open('token.txt').read().strip()

    sync_mode = int(os.environ.get('SYNC_MODE', 0))
    bring_list_name = os.environ.get('BRING_LIST_NAME')

    # Authentication with Google Keep
    keep = Keep()
    try:
        logging.info("Logging into Google Keep...")
        keep.authenticate(google_email, google_token)
        logging.info("Google Keep login successful.")
    except Exception as e:
        logging.error(f"Failed to log into Google Keep: {e}")
        return

    # Authentication with Bring!
    bring = Bring(bring_email, bring_password)
    try:
        logging.info("Logging into Bring!...")
        bring.login()
        logging.info("Bring! login successful.")
    except Exception as e:
        logging.error(f"Failed to log into Bring!: {e}")
        return
    
    keep_list = get_keep_list(keep, keep_list_id)
    bring_items = get_bring_list(bring, bring_list_name)
    
    if keep_list and bring_items:
        sync_lists(keep_list, bring_items, bring, sync_mode)
    
if __name__ == "__main__":
    main()
