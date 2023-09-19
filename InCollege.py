global username
global password

def home_page(): # Home page for all options.
    print("Welcome to InCollege " + username)
    option = ''
    print("Search for a job (Enter s)")
    print("Find someone you know (Enter f)")
    print("Learn a new skill (Enter l)")
    print("Quit (Enter q)")
    while (option != 'q'):
        option = input("Please select an option: ")
        if (option == 's' or option == 'f'):
            print("under construction")
        elif (option == 'l'):
            skills_page() # Move to skills page.
        else:
            print("Invalid option.")
    quit()
            
def skills_page(): # Set of skills on this page
    skillChoice = ''
    print("Select a skill you'd like to learn (Enter 1-5) or return home")
    print("Skill 1: ")
    print("Skill 2: ")
    print("Skill 3: ")
    print("Skill 4: ")
    print("Skill 5: ")
    print("Return home (Enter 6)")
    while (skillChoice != 6):
        skillChoice = int(input("Please select an option: "))
        if (skillChoice >= 1 and skillChoice <= 5):
            print("under construction")
        if (skillChoice == 6):
            break
        else:
            print("Invalid option.")

def main():
    user = input("Welcome to InCollege. Are you an existing user or a new user (Write e for existing, n for new): ")

    if user == 'e':
        valid = False
        while not valid:
            username = input("Please enter your username: ")
            password = input("Please enter password: ")
            # Check if username and password match
                # valid = True
                # print("You have successfully logged in.")
            # else:
                # print("Incorrect username / password, please try again.")
            valid = True; # DELETEME ONCE VALIDATION MADE!!!!!!!!!!!!!!!!!!!!!
        home_page()

    if user == 'n':
        # Check if valid space for new users
        # If not exit program.
        username = input("Please enter your username: ")
        password = input("Please enter password: ")
        # Add new account with username and password
        print("You have successfully logged in.")
        home_page()
    
    return None

if __name__=="__main__":
    main()