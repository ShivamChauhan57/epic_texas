from getpass import getpass
import hashlib
import requests
import sys
import json

class Menu:
    def __init__(self, url):
        self.url = url
        self.access_token = None
        self.mode = 'log-in'

    def main(self):
        while True:
            options, actions = tuple(zip(*self.options()))
            print('Availaible actions:\n{}'.format('\n'.join(f'{i + 1}: {option}' for i, option in enumerate(options))))

            try:
                action = actions[int((input('Enter choice (enter the index): ')).strip()) - 1]
                action()
            except (ValueError, IndexError):
                print('Invalid response, try again.')
            
            print()

    def options(self):
        options = None
        if self.mode == 'log-in':
            options = [
                ('InCollege Video', lambda: print('Video is now playing')),
                ('Log in', self.login),
                ('Sign up', self.signup),
                ('Lookup user', self.lookup_user),
                ('Discover users', self.discover_users),
                ('Useful links', lambda: self.change_mode('useful links')),
                ('InCollege Important Links', lambda: self.change_mode('incollege links')),
                ('Exit', sys.exit)
            ]
        elif self.mode == 'main':
            options = [
                ('See profile', self.see_profile),
                ('Discover users', self.discover_users),
                ('Follow a user', self.follow),
                ('See your followers', self.list_followers),
                ('Job search/internship', lambda: self.change_mode('job search/internship')),
                ('Useful links', lambda: self.change_mode('useful links')),
                ('InCollege Important Links', lambda: self.change_mode('incollege links')),
                ('Log out', self.logout)
            ]
        elif self.mode == 'job search/internship':
            options = [
                ('See job postings', self.get_job_postings),
                ('Post a job', self.post_job),
                ('Return to main menu', lambda: self.change_mode('main')),
            ]
        elif self.mode == 'useful links':
            options = [
                ('General', lambda: self.change_mode('general')),
                ('Browse InCollege', self.under_construction),
                ('Business Solutions', self.under_construction),
                ('Directories', self.under_construction),
                ('Go back', lambda: self.change_mode('main' if self.access_token else 'log-in'))
            ]
        elif self.mode == 'general':
            about_message = 'InCollege: Welcome to InCollege, the world\'s largest college student network with many users in many countries and territories worldwide.'
            press_message = 'InCollege Pressroom: Stay on top of the latest news, updates, and reports.'

            options = [
                ('Help Center', lambda: print('We\'re here to help')),
                ('About', lambda: print(about_message)),
                ('Press', lambda: print(press_message)),
                ('Blog', self.under_construction),
                ('Careers', self.under_construction),
                ('Developers', self.under_construction),
                ('Go back', lambda: self.change_mode('useful links'))
            ]

            if self.access_token == None:
                options = [('Sign Up', self.signup)] + options

        elif self.mode == 'incollege links':
            cookie_policy = '''\nCookie Policy

Last Updated: 10/02/2023

This Cookie Policy explains how [Your Website Name] ("we," "us," or "our") uses cookies and similar tracking technologies on our website. By using our website, you consent to the use of cookies as described in this policy.

1. What Are Cookies?

Cookies are small text files that are placed on your device (computer, tablet, smartphone) when you visit our website. They serve various purposes, including enhancing your browsing experience, providing analytics data, and delivering personalized content and advertisements.

2. Types of Cookies We Use
We use different types of cookies for various purposes:

a. Essential Cookies:
These cookies are necessary for the basic functionality of our website. They enable features such as navigation, login, and access to secure areas. You cannot opt out of essential cookies as they are required for the website to function properly.

b. Analytical Cookies:
We use analytical cookies to collect information about how you interact with our website. This data helps us understand user behavior, improve our website, and measure the effectiveness of our content. Analytical cookies may include:
Google Analytics: These cookies are used to track user interactions on our website. You can learn more about Google Analytics and opt out here.

c. Advertising Cookies:

We work with third-party advertising partners to display advertisements on our website. These partners may use advertising cookies to deliver personalized ads based on your interests and online behavior. Advertising cookies may include:

[Ad 1]: You can review their privacy policy and opt-out options on their website.
[Ad 2]: You can review their privacy policy and opt-out options on their website.
d. Functional Cookies:

Functional cookies enhance your user experience by remembering your preferences and settings. These cookies may include:

[Function 1]: Description of the function and its purpose.
[Function 2]: Description of the function and its purpose.

3. How Long Do Cookies Stay on Your Device?

Cookies can have different durations:

Session Cookies: These cookies are temporary and expire when you close your browser.
Persistent Cookies: Persistent cookies remain on your device for a specified period, even after you close your browser.

4. Managing Cookies
You can manage and control cookies through your browser settings. Most browsers allow you to refuse or delete cookies. Please note that disabling cookies may affect your experience on our website.

5. Third-Party Cookies
Some cookies on our website may be set by third-party providers, such as advertising partners and analytics services. These cookies are subject to the privacy policies of the respective third-party providers. You can typically opt out of third-party cookies by visiting the providers' websites.

6. Updates to This Policy
We may update this Cookie Policy to reflect changes in our cookie usage or legal requirements. Any updates will be posted on this page.

7. Contact Us
If you have any questions or concerns about our Cookie Policy, please contact us at [Contact Information].
'''
            privacy_policy = '''\nPrivacy Policy

Last Updated: 10/02/2023

This Program ("we," "us," or "our") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your personal information when you visit our website or use our services. By accessing or using our website, you consent to the practices described in this Privacy Policy.

1. Information We Collect

a. Personal Information: We may collect personal information that you voluntarily provide to us, such as your name, email address, and any other information you choose to provide when contacting us or using our services.

b. Automatically Collected Information: We may collect certain information automatically when you visit our website, including your IP address, browser type, operating system, and usage patterns. We may use cookies and similar technologies to gather this information.

2. How We Use Your Information

We may use your personal information for the following purposes:

a. To provide and improve our website and services.
b. To respond to your inquiries and requests.
c. To send you updates, newsletters, and promotional materials if you have consented to receive them.
d. To monitor and analyze website usage and trends.

3. Disclosure of Your Information

We may share your personal information with third parties in the following situations:

a. With your consent.
b. To comply with legal obligations.
c. To protect our rights, privacy, safety, or property, or that of our users or third parties.

4. Your Choices

You have the following rights regarding your personal information:

a. Access: You can request access to the personal information we hold about you.
b. Correction: You can request correction of any inaccurate or incomplete personal information.
c. Deletion: You can request the deletion of your personal information.
d. Opt-Out: You can opt out of receiving promotional emails from us.

5. Security

We take reasonable measures to protect your personal information from unauthorized access, disclosure, or alteration. However, please be aware that no method of transmission over the internet or electronic storage is completely secure.

6. Links to Other Websites

Our website may contain links to third-party websites or services. We are not responsible for the privacy practices or content of these websites. We encourage you to review the privacy policies of any third-party sites you visit.

7. Changes to This Privacy Policy

We may update this Privacy Policy to reflect changes in our practices or legal requirements. Any updates will be posted on this page.

8. Contact Us

If you have any questions or concerns about our Privacy Policy, please contact us at [Contact Information].
'''
            copyright_policy='''Copyright Policy

Last Updated: [Date]

[Your Website Name] ("we," "us," or "our") respects the intellectual property rights of others and expects our users to do the same. This Copyright Policy outlines our commitment to protecting copyrights and intellectual property on our website.

1. Copyright Ownership

a. All content, including text, images, graphics, videos, and other materials displayed on our website, is protected by copyright and other intellectual property laws.

b. We either own the copyright to the content on our website or have obtained the necessary licenses or permissions to use the content.

2. Use of Our Content

a. You may access and view the content on our website for personal, non-commercial purposes only.

b. You may not copy, reproduce, distribute, publish, display, modify, or create derivative works from any content on our website without our explicit written permission or as permitted by applicable copyright laws.

3. User-Generated Content

a. Users who contribute content to our website, such as comments, reviews, or forum posts, must ensure they have the necessary rights or permissions to use copyrighted materials.

b. By submitting content to our website, users grant us a non-exclusive, royalty-free, worldwide license to use, reproduce, modify, distribute, and display the content for the purpose of operating and promoting our website.

4. Copyright Infringement Claims

a. If you believe that your copyright-protected work has been used on our website in a way that constitutes copyright infringement, please provide our designated Copyright Agent with the following information:

A physical or electronic signature of the copyright owner or authorized representative.
Identification of the copyrighted work claimed to have been infringed.
Identification of the allegedly infringing material on our website, including its location.
Your contact information, including name, address, phone number, and email address.
A statement that you have a good-faith belief that the use of the copyrighted material is not authorized by the copyright owner, its agent, or the law.
A statement, made under penalty of perjury, that the information provided in the notice is accurate and that you are the copyright owner or authorized to act on their behalf.
b. Our designated Copyright Agent for notice of claims of copyright infringement can be reached at:

[Copyright Agent Name]
[Copyright Agent Address]
[Copyright Agent Email]
[Copyright Agent Phone]

5. Counter-Notification

a. If you believe that your content was removed or disabled in error or as a result of misidentification, you may submit a counter-notification to our Copyright Agent. The counter-notification must include:

Your physical or electronic signature.
Identification of the material that has been removed or to which access has been disabled.
A statement, under penalty of perjury, that you have a good-faith belief that the material was removed or disabled as a result of mistake or misidentification.
Your contact information, including name, address, phone number, and email address.
A statement that you consent to the jurisdiction of the federal district court located within [Your Jurisdiction], and that you will accept service of process from the person who provided the original copyright infringement notification or an agent of such person.
6. Changes to This Copyright Policy

We may update this Copyright Policy to reflect changes in our practices or legal requirements. Any updates will be posted on this page.

7. Contact Us

If you have any questions or concerns about our Copyright Policy, please contact us at [Contact Information].'''
           
            copyright_notice = "InCollege © 2023 All Rights Reserved."

            about = """ InCollege: We are a community of students who understand the transition from college to the job market. We built this application to assist in this transition.
            """
            accessibility = """InCollege is committed to providing a website that is accessible to the widest possible audience, regardless of technology or ability """

            user_agreement = """
            This User Agreement is a legal agreement between you and InCollege governing your use of the Connectify platform, including its website, mobile applications, and related services. By using the Platform, you agree to be bound by the terms and conditions of this Agreement.

            1. Dont hack us.
            2. Be nice.
            """
            brand_policy = """
            Brand Policy - InCollege
            Effective Date: 10/2/2023

            1. Introduction

            This Brand Policy document outlines the guidelines and standards for the consistent representation of the company brand across all communications.

            2. Logo

            Please use our offical logo.
            """

            options = [
                ('Copyright Notice', lambda: print(copyright_notice)),
                ('About', lambda: print(about)),
                ('Accessibility', lambda: print(accessibility)),
                ('User Agreement',lambda: print(user_agreement)),
                ('Privacy Policy',lambda: print(privacy_policy)),
                ('Cookie Policy', lambda: print(cookie_policy)),
                ('Copyright Policy', lambda: print(copyright_policy)),
                ('Brand Policy', lambda: print(brand_policy)),
                ('Guest Controls', lambda: self.change_mode('guest controls')),
                ('Languages', lambda: self.change_mode('languages')),
                ('Go back', lambda: self.change_mode('main')),
            ]
        elif self.mode == 'guest controls':
            on = "ON"
            off = "ON"
            options = [
            ('InCollege Email', lambda: print("InCollege Email",off)),
            ('SMS', lambda: print("SMS", on)),
            ('Targeted Advertising', lambda: print("Targeted Advertising", on)),
            ('Go back', lambda: self.change_mode('incollege links')),

                   
            ]
        elif self.mode == 'languages':
            options = [
                ('English', lambda: print("\nLanguage set to English")),
                ('Spanish', lambda: print("\nIdioma configurado en español")),
                ('Go Back', lambda: self.change_mode('incollege links'))
            ]
            
        return options

    def change_mode(self, new_mode):
        self.mode = new_mode
        if self.options() == None:
            raise Exception(f'Invalid mode: {self.mode}')

    def under_construction(self):
        print('Under construction')
        
    def login(self):
        username = input('Please enter your username: ')
        passwordHash = hashlib.sha256(getpass('Enter your password: ').encode()).hexdigest()

        data = {
            'username': username,
            'passwordHash': passwordHash
        }

        response = requests.post(f'{self.url}/login', data=json.dumps(data), headers={ 'Content-Type': 'application/json' })
        if response.status_code == 200:
            self.access_token = response.json()['token']
            print('Login successful.')
            self.change_mode('main')
        else:
            print('Login unsuccessful.')

    def logout(self):
        self.access_token = None
        self.change_mode('log-in')

    def signup(self):
        def username_exists(username):
            try:
                return any(username == user['username'] for user in requests.get(f'{self.url}/list-users').json())
            except:
                return False    # signing up will be unsuccessful regardless

        username = input('Please enter your username: ')
        if username_exists(username):
            print('Username not available!')
            return

        fullname = input('Please enter your full name: ').strip().split(' ')
        assert len(fullname) >= 2

        password = getpass('Enter your password: ')
        if not (len(password) >= 8 and any(chr(ord('0') + i) in password for i in range(10))):
            print('Password is not secure, should be at least eight characters and must contain a number.')
            return

        data = {
            'username': username,
            'firstname': fullname[0],
            'lastname': fullname[-1],
            'passwordHash': hashlib.sha256(password.encode()).hexdigest()
        }

        response = requests.post(f'{self.url}/add-user', data=json.dumps(data), headers={ 'Content-Type': 'application/json' })
        if response.status_code == 200:
            print('You have successfully signed up! Please log in now.')
        else:
            print('Sign up unsuccessful. Please try again.')

    def see_profile(self):
        response = requests.get(f'{self.url}/profile', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            username, firstname, lastname = tuple(response.json().values())
            print(f'Username: {username}')
            print(f'First name: {firstname}')
            print(f'Last name: {lastname}')
        elif response.status_code == 401:
            print('Error retrieving profile info: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print('Error retrieving profile info.')

    def discover_users(self):
        response = requests.get(f'{self.url}/list-users')
        if response.status_code != 200:
            print('Error retrieving user list')

        if len(users := response.json()):
            for user in response.json():
                print(' '.join(user.values()))
        else:
            print('No users yet.')

    def lookup_user(self):
        firstname = input('Enter the user\'s first name: ').strip()
        lastname = input('Enter the user\'s last name: ').strip()

        response = requests.post(f'{self.url}/lookup-user', data=json.dumps({ 'firstname': firstname, 'lastname': lastname }))

        if response.status_code == 200:
            if response.json()['matches']:
                print(f'{firstname} {lastname} is a part of the InCollege system.')
            else:
                print(f'{firstname} {lastname} is not yet a part of the InCollege system yet.')
        else:
            print('Unable to lookup whether user is part of the InCollege system')

    def follow(self):
        user_to_follow = input('Enter the username of the user to follow: ')
        response = requests.post(f'{self.url}/follow', data=json.dumps({ 'username': user_to_follow }), headers={ 'Authorization': f'Bearer {self.access_token}' })

        if response.status_code == 200:
            print(f'You are now following {user_to_follow}')
        elif response.status_code == 401:
            print(f'Unable to follow {user_to_follow}: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print(f'Unable to follow {user_to_follow}.')

    def list_followers(self):
        response = requests.get(f'{self.url}/followers', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            if len(users := response.json()):
                for user in users:
                    print(' '.join(user.values()))
            else:
                print('You have no followers')
        elif response.status_code == 401:
            print(f'Error retrieving follower list: permission denied. If you haven\'t logged in yet, please do so. If you have, consider doing so again.')
        else:
            print('Error retrieving follower list')

    def post_job(self):
        data = dict()
        for field in ['title', 'description', 'employer', 'location', 'salary']:
            data[field] = input(f'Enter the {field}: ').strip()
        try:
            assert data['salary'][0] == '$'
            data['salary'] = int(data['salary'][1:])
        except (AssertionError, ValueError):
            print('Invalid salary, must be a number which begins with $')
            return

        response = requests.post(f'{self.url}/post-job', data=json.dumps(data), headers={ 'Content-Type': 'application/json', 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code == 200:
            print('Job posting created successfully.')
        else:
            print('Error creating job posting.')

    def get_job_postings(self):
        response = requests.get(f'{self.url}/job-postings', headers={ 'Authorization': f'Bearer {self.access_token}' })
        if response.status_code != 200:
            print('Error fetching job postings.')
            return

        if len(job_postings := response.json()):
            for posting in job_postings:
                posting['salary'] = f'${posting["salary"]}'
                print('\n'.join(f'{key}: {value}' for key, value in posting.items()))
        else:
            print('No job postings found.')

if __name__ == '__main__':
    print('Here is a student success story from Raunak Chhatwal: I was a struggling student with a 2.069 GPA and no internship, so my hopes were down. Fortunately, with InCollege, I was able to land an entry level position with the mighty Sinaloa cartel in their armed robotics division.\n')

    url = sys.argv[1] if len(sys.argv) > 1 else 'http://raunak.us'
    menu = Menu(url)
    menu.main()
