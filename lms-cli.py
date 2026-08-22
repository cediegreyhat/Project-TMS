"""Project-LMS Command-Line Interface."""

import datetime
import getpass
import re
import traceback

from colorama import Fore, Style, init

from database import DatabaseManager
from service import ServiceError, ToolService

init(autoreset=True)

# SQL keywords that are NOT allowed in the CLI read-only console.
# Any statement that *starts with* one of these prefixes is rejected before
# it ever reaches sqlite3, eliminating the trivially-bypassed prefix-only
# check that a previous version relied on.
_BLOCKED_SQL_KEYWORDS = (
    "insert", "update", "delete", "drop", "alter", "create", "replace",
    "truncate", "attach", "detach", "vacuum", "pragma writable",
    "pragma writable_schema", "reindex", "savepoint", "release",
    "rollback", "commit", "begin", "end", "grant", "revoke",
)


def print_banner():
    banner = '''
 _____                                                                     _____
( ___ )                                                                   ( ___ )
 |   |~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|   |
 |   | 8""""8                                         8     8""8""8 8""""8 |   |
 |   | 8    8 eeeee  eeeee    e  eeee eeee eeeee      8     8  8  8 8      |   |
 |   | 8eeee8 8   8  8  88    8  8    8  8   8        8e    8e 8  8 8eeeee |   |
 |   | 88     8eee8e 8   8    8e 8eee 8e     8e  eeee 88    88 8  8     88 |   |
 |   | 88     88   8 8   8 e  88 88   88     88       88    88 8  8 e   88 |   |
 |   | 88     88   8 8eee8 8ee88 88ee 88e8   88       88eee 88 8  8 8eee88 |   |
 |___|~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~|___|
(_____)                                                                   (_____)
'''
    print(Fore.CYAN + banner + Style.RESET_ALL)


class Session:
    """Tracks the authenticated user and their role for the CLI session."""

    def __init__(self, user):
        self.user_id = user["id"]
        self.username = user["username"]
        self.is_admin = bool(user.get("is_admin"))


def _prepare_table_data(rows, headers):
    if isinstance(rows[0], dict):
        if headers is None:
            headers = list(rows[0].keys())
        data = [[str(row.get(h, "") if row.get(h, "") is not None else "") for h in headers]
                for row in rows]
    else:
        data = [[str(cell) if cell is not None else "" for cell in row] for row in rows]
        if headers and len(headers) != len(rows[0]):
            headers = [f"Col{i+1}" for i in range(len(rows[0]))]
    return headers, data


def print_table(rows, headers=None):
    if not rows:
        print(Fore.YELLOW + "No data to display." + Style.RESET_ALL)
        return
    headers, data = _prepare_table_data(rows, headers)
    col_widths = [len(str(h)) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))
    fmt = " | ".join([f"{{:<{w}}}" for w in col_widths])
    sep = "-+-".join(["-" * w for w in col_widths])
    print(Fore.MAGENTA + fmt.format(*headers) + Style.RESET_ALL)
    print(sep)
    for row in data:
        print(fmt.format(*row))


def get_valid_int(prompt, allow_blank=False):
    while True:
        value = input(Fore.CYAN + prompt + Style.RESET_ALL).strip()
        if allow_blank and not value:
            return None
        if value.isdigit():
            return int(value)
        print(Fore.RED + "Invalid input. Please enter a valid integer.")


def get_valid_str(prompt, allow_blank=False):
    while True:
        value = input(Fore.CYAN + prompt + Style.RESET_ALL).strip()
        if allow_blank or value:
            return value
        print(Fore.RED + "Invalid input. Please enter a non-empty string.")


def require_admin(session):
    if not session.is_admin:
        print(Fore.RED + "Access denied: this operation requires an admin account." + Style.RESET_ALL)
        return False
    return True


def handle_add_tool(svc, session):
    try:
        name = get_valid_str("Enter tool name: ")
        category = get_valid_str("Enter tool category: ")
        condition = get_valid_str("Enter tool condition (Good/Fair/Poor): ").capitalize()
        while condition not in ["Good", "Fair", "Poor"]:
            print(Fore.RED + "Invalid condition. Please enter 'Good', 'Fair', or 'Poor'.")
            condition = get_valid_str("Enter tool condition (Good/Fair/Poor): ").capitalize()
        quantity = get_valid_int("Enter quantity: ")
        location = get_valid_str("Enter location: ")
        svc.add_tool(name, category, condition, quantity, location, actor=session.user_id)
        print(Fore.GREEN + f"Tool '{name}' added successfully!" + Style.RESET_ALL)
    except ServiceError as e:
        print(Fore.RED + str(e) + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error adding tool: {e}" + Style.RESET_ALL)


def handle_view_tools(db):
    try:
        tools = db.fetch_all_tools()
        if not tools:
            print(Fore.YELLOW + "No tools found in the inventory.")
            return
        headers = list(tools[0].keys()) if isinstance(tools[0], dict) else None
        print_table(tools, headers)
        print(Fore.BLUE + f"\nTotal tools: {len(tools)}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error fetching tools: {e}" + Style.RESET_ALL)


def handle_update_tool(svc, session):
    try:
        tool_id = get_valid_int("Enter the Tool ID to update: ")
        print(Fore.YELLOW + "Leave fields blank to skip updating them." + Style.RESET_ALL)
        updates = {
            "name": get_valid_str("New tool name: ", allow_blank=True),
            "category": get_valid_str("New tool category: ", allow_blank=True),
            "condition": get_valid_str("New tool condition (Good/Fair/Poor): ", allow_blank=True).capitalize(),
            "quantity": get_valid_int("New quantity: ", allow_blank=True),
            "location": get_valid_str("New location: ", allow_blank=True),
        }
        updates = {k: v for k, v in updates.items() if v is not None and v != ""}
        if not updates:
            print(Fore.YELLOW + "No updates provided. Operation cancelled." + Style.RESET_ALL)
            return
        if svc.update_tool(tool_id, actor=session.user_id, **updates):
            print(Fore.GREEN + "Tool updated successfully!" + Style.RESET_ALL)
        else:
            print(Fore.YELLOW + "No changes made (tool not found or no valid fields).")
    except ServiceError as e:
        print(Fore.RED + str(e) + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error updating tool: {e}" + Style.RESET_ALL)


def handle_delete_tool(svc, session):
    try:
        tool_id = get_valid_int("Enter the Tool ID to delete: ")
        confirm = input(Fore.RED + f"Are you sure you want to delete tool {tool_id}? (y/N): " + Style.RESET_ALL).strip().lower()
        if confirm != "y":
            print(Fore.YELLOW + "Delete cancelled." + Style.RESET_ALL)
            return
        svc.delete_tool(tool_id, actor=session.user_id)
        print(Fore.GREEN + f"Tool {tool_id} deleted successfully!" + Style.RESET_ALL)
    except ServiceError as e:
        print(Fore.RED + str(e) + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error deleting tool: {e}" + Style.RESET_ALL)


def handle_borrow_tool(db, session):
    try:
        available_tools = db.fetch_tools_by_status("available")
        if not available_tools:
            print(Fore.YELLOW + "No tools are currently available for borrowing." + Style.RESET_ALL)
            return
        print(Fore.CYAN + "\nAvailable Tools for Borrowing:")
        print_table(available_tools, ["tool_id", "name", "status", "quantity"])
        tool_id = get_valid_int("Enter the Tool ID to borrow: ")
        # Quantity + ownership semantics: a tool is fully free iff stock > 0
        # AND no one currently holds a unit. This is the right "available"
        # signal for both single-unit and multi-quantity tools.
        selected = db.fetch_tool_by_id(tool_id)
        if not selected or selected["quantity"] <= 0 or selected.get("user_id") is not None:
            print(Fore.RED + "Invalid selection. The tool is either unavailable or does not exist." + Style.RESET_ALL)
            return
        borrower_name = session.username
        borrow_date = datetime.date.today().isoformat()
        if db.borrow_tool(tool_id, session.user_id, borrower_name, borrow_date):
            print(Fore.GREEN + f"Tool '{selected['name']}' borrowed successfully!" + Style.RESET_ALL)
        else:
            print(Fore.RED + "Failed to borrow tool." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error borrowing tool: {e}" + Style.RESET_ALL)


def handle_return_tool(db, session):
    try:
        borrowed = db.fetch_borrowed_by_user(session.user_id)
        if not borrowed:
            print(Fore.YELLOW + "You have no borrowed tools to return." + Style.RESET_ALL)
            return
        print(Fore.CYAN + "\nYour Borrowed Tools:")
        print_table(borrowed, ["tool_id", "name", "status", "borrow_date"])
        tool_id = get_valid_int("Enter the Tool ID to return: ")
        owned_ids = [t["tool_id"] for t in borrowed]
        if tool_id not in owned_ids:
            print(Fore.RED + "Access denied: you can only return tools you borrowed." + Style.RESET_ALL)
            return
        return_date = datetime.date.today().isoformat()
        if db.return_tool(tool_id, session.user_id, return_date):
            print(Fore.GREEN + f"Tool {tool_id} returned successfully!" + Style.RESET_ALL)
        else:
            print(Fore.RED + "Failed to return tool (not owned or already returned)." + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"Error returning tool: {e}" + Style.RESET_ALL)


def handle_search_tools(db):
    try:
        keyword = get_valid_str("Enter search keyword (tool name or category): ")
        results = db.search_tool(keyword)
        if not results:
            print(Fore.YELLOW + "No tools found matching the search criteria.")
        else:
            headers = list(results[0].keys()) if isinstance(results[0], dict) else None
            print(Fore.CYAN + "\nSearch Results:")
            print_table(results, headers)
    except Exception as e:
        print(Fore.RED + f"Error searching for tools: {e}" + Style.RESET_ALL)


def handle_clear_data(svc, session):
    confirmation = input(Fore.RED + "Type 'YES' to confirm clearing ALL tools and transactions: " + Style.RESET_ALL)
    if confirmation.upper() == "YES":
        try:
            svc.clear_inventory(session.user_id)
            print(Fore.GREEN + "All data cleared successfully." + Style.RESET_ALL)
        except ServiceError as e:
            print(Fore.RED + str(e) + Style.RESET_ALL)
    else:
        print(Fore.YELLOW + "Operation cancelled.")


def handle_execute_sql(db, session):
    """Admin-only read-only SQL console. Destructive statements are blocked."""
    if not require_admin(session):
        return
    sql_command = input(Fore.YELLOW + "Enter SQL command (SELECT/PRAGMA/EXPLAIN): " + Style.RESET_ALL).strip()
    if not sql_command:
        return
    
    # Normalize and validate prefix
    stripped = sql_command.lstrip().lower()
    allowed_prefixes = ("select", "pragma", "explain", "with")
    if not any(stripped.startswith(p) for p in allowed_prefixes):
        print(Fore.RED + "Blocked: statement must start with SELECT, PRAGMA, EXPLAIN, or WITH.")
        return
    
    # Keyword-based safeguard: block destructive operations even in subqueries or multi-statements.
    for word in _BLOCKED_SQL_KEYWORDS:
        if re.search(rf"\b{re.escape(word)}\b", stripped):
            print(Fore.RED + f"Blocked: forbidden keyword '{word}' detected.")
            return
    
    try:
        results = db._execute_query(sql_command, fetch=True)
        if not results:
            print(Fore.YELLOW + "No results found.")
        else:
            print(Fore.CYAN + "\nQuery Results:")
            for row in results:
                if isinstance(row, dict):
                    print(Fore.CYAN + "\t".join(str(v) for v in row.values()))
                else:
                    print(Fore.CYAN + "\t".join(map(str, row)))
    except Exception as e:
        print(Fore.RED + f"Error executing SQL command: {e}" + Style.RESET_ALL)


def account_login(db):
    print(Fore.YELLOW + "=== Login ===")
    username = get_valid_str("Enter username: ")
    password = getpass.getpass("Enter password: ")
    user = db.authenticate(username, password)
    if user:
        print(Fore.GREEN + "Login successful!" + Style.RESET_ALL)
        print(Fore.GREEN + f"Welcome, {user['name'] or user['username']} " +
              ("(Admin)" if user["is_admin"] else "(User)") + Style.RESET_ALL)
        return Session(user)
    print(Fore.RED + "Invalid username or password. Please try again." + Style.RESET_ALL)
    return None


def get_menu_choice():
    while True:
        choice = input(Fore.YELLOW + "Enter your choice: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= 10:
            return choice
        print(Fore.RED + "Invalid choice. Please enter a number between 1 and 10.")


def main_menu(session):
    print(Fore.GREEN + "\n=== Project-LMS [CLI] ===" + Style.RESET_ALL)
    menu_options = [
        "1. Add Tool",
        "2. View All Tools",
        "3. Update Tool",
        "4. Delete Tool",
        "5. Borrow Tool",
        "6. Return Tool",
        "7. Search Tools",
        "8. Clear All Data (Admin Only)",
        "9. Execute SQL Command (Admin Only)",
        "10. Exit",
    ]
    for option in menu_options:
        print(Fore.YELLOW + f"{option}" + Style.RESET_ALL)


if __name__ == "__main__":
    db = DatabaseManager("db/inventory.db")
    svc = ToolService(db)
    db.check_and_add_default_data()
    print_banner()
    session = None
    try:
        while session is None:
            session = account_login(db)
        while True:
            main_menu(session)
            choice = get_menu_choice()
            if choice == "1":
                handle_add_tool(svc, session)
            elif choice == "2":
                handle_view_tools(db)
            elif choice == "3":
                handle_update_tool(svc, session)
            elif choice == "4":
                handle_delete_tool(svc, session)
            elif choice == "5":
                handle_borrow_tool(db, session)
            elif choice == "6":
                handle_return_tool(db, session)
            elif choice == "7":
                handle_search_tools(db)
            elif choice == "8":
                handle_clear_data(svc, session)
            elif choice == "9":
                handle_execute_sql(db, session)
            elif choice == "10":
                print(Fore.GREEN + "Thank you for using Project-LMS. Goodbye!" + Style.RESET_ALL)
                break
    except Exception as e:
        print(Fore.RED + f"Unexpected error: {e}" + Style.RESET_ALL)
        traceback.print_exc()
    finally:
        db.close()
