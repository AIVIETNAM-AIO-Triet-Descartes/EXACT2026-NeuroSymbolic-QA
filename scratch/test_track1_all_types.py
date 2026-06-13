import urllib.request
import json
import re

url = "http://13.229.155.181:9000/predict"

test_cases = {
    "type1_mc": [
        {
            "query_id": "mc_test_1",
            "type": "type1",
            "query": "Based on the premises, which statement is logically supported?\nA. John can access the main server\nB. John is not a system administrator\nC. John has no clearance\nD. John cannot log in",
            "premises": [
                "If someone is a system administrator and has high clearance, then they can access the main server.",
                "John is a system administrator.",
                "John has high clearance."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "A",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "mc_test_2",
            "type": "type1",
            "query": "Which option must be true?\n(a) Lab B is active\n(b) Lab B is inactive\n(c) Lab A is active\n(d) Lab A is inactive",
            "premises": [
                "If Lab A completed the safety check, then Lab B is active.",
                "Lab A completed the safety check."
            ],
            "options": ["(a)", "(b)", "(c)", "(d)"],
            "expected_answer": "(a)",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "mc_test_3",
            "type": "type1",
            "query": "Which of the following is correct?\n1. Alice may join Study Beta\n2. Alice cannot join Study Beta\n3. Alice is not qualified\n4. Alice has no supervisor approval",
            "premises": [
                "If a scientist has supervisor approval and is certified, then they may join Study Beta.",
                "Alice has supervisor approval.",
                "Alice is certified."
            ],
            "options": ["1", "2", "3", "4"],
            "expected_answer": "1",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "mc_test_4",
            "type": "type1",
            "query": "Which conclusion holds?\n- Asha is listed as an active contributor\n- Asha is not listed\n- Asha has no lab access\n- Asha has no ethics training",
            "premises": [
                "Every researcher who completes the training and is approved is listed as an active contributor.",
                "Asha completes the training.",
                "Asha is approved."
            ],
            "options": ["Asha is listed as an active contributor", "Asha is not listed", "Asha has no lab access", "Asha has no ethics training"],
            "expected_answer": "Asha is listed as an active contributor",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "mc_test_5",
            "type": "type1",
            "query": "Based on the premises, which option is true?\nA) Bob is a researcher\nB) Bob is a manager\nC) Bob is a director\nD) Bob is a coordinator",
            "premises": [
                "If Bob leads the project, then Bob is a manager.",
                "Bob leads the project."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "B",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "mc_test_6",
            "type": "type1",
            "query": "Which option must be true?\nA. Device X is connected\nB. Device X is not connected\nC. Device X is malfunctioning\nD. Device X is a router",
            "premises": [
                "If a device is connected to the network, it has an IP address.",
                "Device X does not have an IP address."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "B",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "mc_test_7",
            "type": "type1",
            "query": "Which of the following is true?\n(a) Bob can see the user list\n(b) Bob cannot view the dashboard\n(c) Bob is an administrator\n(d) Bob cannot see the user list",
            "premises": [
                "If a user is logged in, they can view the dashboard.",
                "If a user can view the dashboard, they can see the user list.",
                "User Bob is logged in."
            ],
            "options": ["(a)", "(b)", "(c)", "(d)"],
            "expected_answer": "(a)",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "mc_test_8",
            "type": "type1",
            "query": "Based on the premises, which statement is correct?\n1. The server is in Server Room B\n2. The server is in both rooms\n3. The server is offline\n4. The server is in Server Room A",
            "premises": [
                "The server is either in Server Room A or Server Room B.",
                "The server is not in Server Room A."
            ],
            "options": ["1", "2", "3", "4"],
            "expected_answer": "1",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "mc_test_9",
            "type": "type1",
            "query": "Which statement holds?\nA) The query is fast\nB) It causes a timeout\nC) The index is present\nD) No timeout occurs",
            "premises": [
                "If a database query is slow and index is missing, it causes a timeout.",
                "The database query is slow.",
                "The index is missing."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "B",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "mc_test_10",
            "type": "type1",
            "query": "Which option is correct?\nA) File Y is secure\nB) File Y is not secure\nC) File Y is deleted\nD) File Y is encrypted",
            "premises": [
                "If a file is not encrypted, it is not secure.",
                "File Y is not encrypted."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "B",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "mc_test_11",
            "type": "type1",
            "query": "Based on the premises, which statement is true?\nA. The client shows a connection error\nB. The database is not corrupted\nC. The server does not fail\nD. The client is working perfectly",
            "premises": [
                "If the database is corrupted, the server fails.",
                "If the server fails, the client shows a connection error.",
                "The database is corrupted."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "A",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "mc_test_12",
            "type": "type1",
            "query": "Which statement must be correct?\nA) Bob uses a fingerprint to login\nB) Bob cannot login\nC) Bob uses both methods\nD) Bob is an administrator",
            "premises": [
                "A user must use either a password or a fingerprint to login.",
                "User Bob does not use a password to login."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "A",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "mc_test_13",
            "type": "type1",
            "query": "Which option is correct?\n1. File X is infected with malware\n2. File X is not infected with malware\n3. File X is a system file\n4. File X is empty",
            "premises": [
                "If a file is infected with malware, it is deleted.",
                "File X is not deleted."
            ],
            "options": ["1", "2", "3", "4"],
            "expected_answer": "2",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "mc_test_14",
            "type": "type1",
            "query": "Which statement holds?\nA. Alice is not a developer\nB. Bob is a tester\nC. Alice is a designer\nD. Bob is not a tester",
            "premises": [
                "Alice is a developer and Bob is a tester."
            ],
            "options": ["A", "B", "C", "D"],
            "expected_answer": "B",
            "expected_premises": [0]
        },
        {
            "query_id": "mc_test_15",
            "type": "type1",
            "query": "Based on the premises, which option is correct?\n1. Charlie can access the dashboard\n2. Charlie cannot access the dashboard\n3. Charlie is an administrator\n4. Charlie is logged in",
            "premises": [
                "Only registered users can access the dashboard.",
                "Charlie is not a registered user."
            ],
            "options": ["1", "2", "3", "4"],
            "expected_answer": "2",
            "expected_premises": [0, 1]
        }
    ],
    "type1_yes_no": [
        {
            "query_id": "yes_no_test_1",
            "type": "type1",
            "query": "Is Asha listed as an active contributor?",
            "premises": [
                "If a researcher completed ethics training and has lab access, then that researcher can handle participant data.",
                "If a researcher can handle participant data and has supervisor approval, then that researcher may join Study Alpha.",
                "Every researcher who may join Study Alpha is listed as an active contributor.",
                "Asha completed ethics training.",
                "Asha has lab access.",
                "Asha has supervisor approval."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Yes",
            "expected_premises": [0, 1, 2, 3, 4, 5]
        },
        {
            "query_id": "yes_no_test_2",
            "type": "type1",
            "query": "Is Bob denied entry to the cleanroom?",
            "premises": [
                "If a staff member wears a protective suit, they are not denied entry to the cleanroom.",
                "Bob wears a protective suit."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "No",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_3",
            "type": "type1",
            "query": "Does Alice have system access?",
            "premises": [
                "If a user does not pass the security check, they do not have system access.",
                "Alice did not pass the security check."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "No",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_4",
            "type": "type1",
            "query": "Is Asha qualified to handle participant data?",
            "premises": [
                "If a researcher has ethics training and has lab access, then that researcher is qualified to handle participant data.",
                "Asha has ethics training.",
                "Asha has lab access."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Yes",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "yes_no_test_5",
            "type": "type1",
            "query": "Does Project Delta have funding?",
            "premises": [
                "If a project receives supervisor approval, it has funding.",
                "Project Delta does not receive supervisor approval."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_6",
            "type": "type1",
            "query": "Is Bob verified?",
            "premises": [
                "If a user is verified, they have a badge.",
                "If a user has a badge, they can post comments.",
                "User Bob cannot post comments."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "No",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "yes_no_test_7",
            "type": "type1",
            "query": "Can Alice take AP Calculus?",
            "premises": [
                "If a student is in Grade 12 or passed the placement test, they can take AP Calculus.",
                "Alice passed the placement test."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Yes",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_8",
            "type": "type1",
            "query": "Does Project Alpha receive funding?",
            "premises": [
                "If a project is not approved, it does not receive funding.",
                "Project Alpha is not approved."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "No",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_9",
            "type": "type1",
            "query": "Is Server A online?",
            "premises": [
                "If a server is under maintenance, it is not online.",
                "Server A is under maintenance."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "No",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_10",
            "type": "type1",
            "query": "Does Charlie have a keycard?",
            "premises": [
                "If a person has a keycard, they can open the lab door.",
                "Charlie can open the lab door."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_11",
            "type": "type1",
            "query": "Is Router R1 active?",
            "premises": [
                "If a router is active, it routes packets.",
                "If a router routes packets, it does not drop packets.",
                "Router R1 drops packets."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "No",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "yes_no_test_12",
            "type": "type1",
            "query": "Is Alice in Paris?",
            "premises": [
                "Alice is in either London or Paris.",
                "Alice is not in London."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Yes",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_13",
            "type": "type1",
            "query": "Is File F encrypted?",
            "premises": [
                "It is not true that File F is not encrypted."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Yes",
            "expected_premises": [0]
        },
        {
            "query_id": "yes_no_test_14",
            "type": "type1",
            "query": "Is Project P1 completed?",
            "premises": [
                "If a project is completed, it is archived.",
                "Project P1 is archived."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "yes_no_test_15",
            "type": "type1",
            "query": "Is Device D1 active?",
            "premises": [
                "All active devices must have an IP address.",
                "Device D1 does not have an IP address."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "No",
            "expected_premises": [0, 1]
        }
    ],
    "type1_uncertain": [
        {
            "query_id": "uncertain_test_1",
            "type": "type1",
            "query": "Does Asha have budget approval?",
            "premises": [
                "If a researcher completed ethics training and has lab access, then that researcher can handle participant data.",
                "Asha completed ethics training.",
                "Asha has lab access.",
                "No premise states whether Asha has budget approval."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [3]
        },
        {
            "query_id": "uncertain_test_2",
            "type": "type1",
            "query": "Is Study Alpha fully funded?",
            "premises": [
                "Study Alpha has 12 enrolled participants.",
                "No information is provided about whether Study Alpha is fully funded."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_3",
            "type": "type1",
            "query": "Does Bob have lab access?",
            "premises": [
                "Asha has supervisor approval.",
                "It is unknown whether Bob has lab access."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_4",
            "type": "type1",
            "query": "Has Project Gamma been completed?",
            "premises": [
                "Project Gamma has 3 active contributors.",
                "Whether Project Gamma has been completed is not specified."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_5",
            "type": "type1",
            "query": "Does Asha have a keycard?",
            "premises": [
                "Asha completed ethics training.",
                "No premise states whether Asha has a keycard."
            ],
            "options": ["Yes", "No", "Cannot determine"],
            "expected_answer": "Cannot determine",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_6",
            "type": "type1",
            "query": "Is Alice an administrator?",
            "premises": [
                "If a user is an administrator, they have root access.",
                "Alice has root access."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "uncertain_test_7",
            "type": "type1",
            "query": "Can a request succeed on port 80?",
            "premises": [
                "If a service is running, it listens on port 80.",
                "If a port is open, a request can succeed.",
                "Service X is running."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "uncertain_test_8",
            "type": "type1",
            "query": "Can Bob view the profile page?",
            "premises": [
                "If a user is logged in, they can view the profile page.",
                "Whether user Bob is logged in is not specified."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_9",
            "type": "type1",
            "query": "Is Server C backed up daily?",
            "premises": [
                "Every database is backed up daily.",
                "No information is provided on whether Server C contains a database."
            ],
            "options": ["Yes", "No", "Cannot be determined"],
            "expected_answer": "Cannot be determined",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_10",
            "type": "type1",
            "query": "Is File Z safe?",
            "premises": [
                "If a file is encrypted, it is safe.",
                "File Z is not encrypted.",
                "No premise states whether File Z is safe by other means."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [2]
        },
        {
            "query_id": "uncertain_test_11",
            "type": "type1",
            "query": "Can student John attend the seminar?",
            "premises": [
                "Every registered student can attend the seminar.",
                "No premise states whether student John is registered."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_12",
            "type": "type1",
            "query": "Does the alarm sound?",
            "premises": [
                "If the server temperature exceeds 80 degrees, the alarm sounds.",
                "No information is provided about the current server temperature."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_13",
            "type": "type1",
            "query": "Does Bob have admin permissions?",
            "premises": [
                "Alice has admin permissions.",
                "No statement mentions if Bob has admin permissions."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_14",
            "type": "type1",
            "query": "Is the backup server sync status active?",
            "premises": [
                "The local database is synchronized with the remote database.",
                "Whether the sync status of the backup server is active is unknown."
            ],
            "options": ["Yes", "No", "Cannot determine"],
            "expected_answer": "Cannot determine",
            "expected_premises": [1]
        },
        {
            "query_id": "uncertain_test_15",
            "type": "type1",
            "query": "Can Charlie enter the server room?",
            "premises": [
                "Only employees with badge A or badge B can enter the server room.",
                "Charlie has badge C.",
                "No premise states whether Charlie has badge A."
            ],
            "options": ["Yes", "No", "Uncertain"],
            "expected_answer": "Uncertain",
            "expected_premises": [2]
        }
    ],
    "type1_number": [
        {
            "query_id": "number_test_1",
            "type": "type1",
            "query": "How many enrolled participants does Study Alpha have?",
            "premises": [
                "Study Alpha has 12 enrolled participants.",
                "No premise states whether Asha has budget approval."
            ],
            "options": [],
            "expected_answer": "12",
            "expected_premises": [0]
        },
        {
            "query_id": "number_test_2",
            "type": "type1",
            "query": "How many researchers does the secondary lab have?",
            "premises": [
                "The main lab has 15 researchers.",
                "The secondary lab has 8 fewer researchers than the main lab."
            ],
            "options": [],
            "expected_answer": "7",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "number_test_3",
            "type": "type1",
            "query": "What is the total number of contributors across both projects?",
            "premises": [
                "Project Alpha has 4 active contributors.",
                "Project Beta has 6 active contributors."
            ],
            "options": [],
            "expected_answer": "10",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "number_test_4",
            "type": "type1",
            "query": "How many hours of ethics training are required?",
            "premises": [
                "The standard training is 5 hours.",
                "The advanced training is twice as long as the standard training.",
                "Ethics training is the advanced training."
            ],
            "options": [],
            "expected_answer": "10",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "number_test_5",
            "type": "type1",
            "query": "How many safety certificates must be submitted?",
            "premises": [
                "Each lab must submit 3 safety certificates."
            ],
            "options": [],
            "expected_answer": "3",
            "expected_premises": [0]
        },
        {
            "query_id": "number_test_6",
            "type": "type1",
            "query": "How many minutes does each test case take?",
            "premises": [
                "The total duration of the test suite is 24 minutes.",
                "There are 8 test cases, each taking the same amount of time."
            ],
            "options": [],
            "expected_answer": "3",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "number_test_7",
            "type": "type1",
            "query": "How many GB of RAM does Server C have?",
            "premises": [
                "Server A has 16 GB of RAM.",
                "Server B has twice as much RAM as Server A.",
                "Server C has 8 GB more RAM than Server B."
            ],
            "options": [],
            "expected_answer": "40",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "number_test_8",
            "type": "type1",
            "query": "How many milestones are remaining?",
            "premises": [
                "A project has 10 milestones.",
                "3 milestones were completed last month.",
                "2 milestones were completed this month."
            ],
            "options": [],
            "expected_answer": "5",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "number_test_9",
            "type": "type1",
            "query": "How many team members know both Python and Javascript?",
            "premises": [
                "There are 5 members in the team.",
                "3 members know Python.",
                "4 members know Javascript.",
                "All team members know either Python or Javascript."
            ],
            "options": [],
            "expected_answer": "2",
            "expected_premises": [0, 1, 2, 3]
        },
        {
            "query_id": "number_test_10",
            "type": "type1",
            "query": "What is the maximum allowed temperature in degrees?",
            "premises": [
                "The maximum allowed temperature is 75 degrees."
            ],
            "options": [],
            "expected_answer": "75",
            "expected_premises": [0]
        },
        {
            "query_id": "number_test_11",
            "type": "type1",
            "query": "How many open pull requests are currently in the repository?",
            "premises": [
                "A repository has 20 open pull requests.",
                "5 pull requests are merged.",
                "3 pull requests are closed without merging.",
                "7 new pull requests are opened."
            ],
            "options": [],
            "expected_answer": "19",
            "expected_premises": [0, 1, 2, 3]
        },
        {
            "query_id": "number_test_12",
            "type": "type1",
            "query": "What is the total number of virtual machines across all clusters?",
            "premises": [
                "Each of the 4 clusters has 8 nodes.",
                "Each node hosts 5 virtual machines."
            ],
            "options": [],
            "expected_answer": "160",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "number_test_13",
            "type": "type1",
            "query": "How many projects use both React and Angular?",
            "premises": [
                "There are 10 projects in the company.",
                "6 projects use React.",
                "5 projects use Angular.",
                "Every project uses either React or Angular."
            ],
            "options": [],
            "expected_answer": "1",
            "expected_premises": [0, 1, 2, 3]
        },
        {
            "query_id": "number_test_14",
            "type": "type1",
            "query": "How many steps does Task Gamma require?",
            "premises": [
                "Task Alpha requires 4 steps.",
                "Task Beta requires twice as many steps as Task Alpha.",
                "Task Gamma requires 3 more steps than Task Beta."
            ],
            "options": [],
            "expected_answer": "11",
            "expected_premises": [0, 1, 2]
        },
        {
            "query_id": "number_test_15",
            "type": "type1",
            "query": "How many developers do not know Python?",
            "premises": [
                "There are 15 active developers on the team.",
                "9 developers know Python.",
                "6 developers know only Java."
            ],
            "options": [],
            "expected_answer": "6",
            "expected_premises": [0, 1]
        }
    ],
    "type1_text": [
        {
            "query_id": "text_test_1",
            "type": "type1",
            "query": "Which researcher may join Study Alpha?",
            "premises": [
                "If a researcher completed ethics training and has lab access, then that researcher can handle participant data.",
                "If a researcher can handle participant data and has supervisor approval, then that researcher may join Study Alpha.",
                "Asha completed ethics training.",
                "Asha has lab access.",
                "Asha has supervisor approval."
            ],
            "options": [],
            "expected_answer": "Asha",
            "expected_premises": [0, 1, 2, 3, 4]
        },
        {
            "query_id": "text_test_2",
            "type": "type1",
            "query": "Who is the director of the lab?",
            "premises": [
                "Professor Asha is the lead investigator of Study Alpha.",
                "She is also the director of the lab."
            ],
            "options": [],
            "expected_answer": "Professor Asha",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_3",
            "type": "type1",
            "query": "Which candidate gets the job?",
            "premises": [
                "If a candidate has a PhD and passes the interview, they get the job.",
                "Alice has a PhD and passed the interview.",
                "Bob has a Master's degree and failed the interview."
            ],
            "options": [],
            "expected_answer": "Alice",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_4",
            "type": "type1",
            "query": "Which project receives the funding grant?",
            "premises": [
                "Project Delta meets all criteria for the funding grant.",
                "Project Epsilon is ineligible."
            ],
            "options": [],
            "expected_answer": "Project Delta",
            "expected_premises": [0]
        },
        {
            "query_id": "text_test_5",
            "type": "type1",
            "query": "Who completed the ethics training?",
            "premises": [
                "Asha completed the safety training.",
                "Bob completed the ethics training."
            ],
            "options": [],
            "expected_answer": "Bob",
            "expected_premises": [1]
        },
        {
            "query_id": "text_test_6",
            "type": "type1",
            "query": "Who was born in London?",
            "premises": [
                "Dr. Alan Turing is the father of computer science.",
                "He was born in London."
            ],
            "options": [],
            "expected_answer": "Dr. Alan Turing",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_7",
            "type": "type1",
            "query": "Which team received the cash prize?",
            "premises": [
                "Team Alpha won the annual hackathon.",
                "They received a cash prize of one thousand dollars."
            ],
            "options": [],
            "expected_answer": "Team Alpha",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_8",
            "type": "type1",
            "query": "Who manages Server S1?",
            "premises": [
                "If a server runs Linux, it is managed by Devops.",
                "Server S1 runs Linux."
            ],
            "options": [],
            "expected_answer": "Devops",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_9",
            "type": "type1",
            "query": "Identify where the primary email database is located.",
            "premises": [
                "The primary email database is hosted on Server E.",
                "Server E is located in the London office."
            ],
            "options": [],
            "expected_answer": "London office",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_10",
            "type": "type1",
            "query": "Which department must Alice contact?",
            "premises": [
                "Alice must contact either the HR department or the Tech department.",
                "Alice is not allowed to contact the Tech department."
            ],
            "options": [],
            "expected_answer": "HR department",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_11",
            "type": "type1",
            "query": "Who is the author of the new compiler?",
            "premises": [
                "David is the leader of Team Omega.",
                "He is the author of the new compiler."
            ],
            "options": [],
            "expected_answer": "David",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_12",
            "type": "type1",
            "query": "Who must sign the security report?",
            "premises": [
                "Either Alice or Bob must sign the security report.",
                "Alice is on vacation and cannot sign."
            ],
            "options": [],
            "expected_answer": "Bob",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_13",
            "type": "type1",
            "query": "Who is the security coordinator?",
            "premises": [
                "The database administrator is Sophia.",
                "The security coordinator is Evelyn."
            ],
            "options": [],
            "expected_answer": "Evelyn",
            "expected_premises": [1]
        },
        {
            "query_id": "text_test_14",
            "type": "type1",
            "query": "Identify where Project Zeta is hosted.",
            "premises": [
                "Project Zeta is a major software project.",
                "It is hosted on GitHub Enterprise."
            ],
            "options": [],
            "expected_answer": "GitHub Enterprise",
            "expected_premises": [0, 1]
        },
        {
            "query_id": "text_test_15",
            "type": "type1",
            "query": "Who can deploy the release?",
            "premises": [
                "Only Alice can deploy the release.",
                "Bob cannot deploy the release."
            ],
            "options": [],
            "expected_answer": "Alice",
            "expected_premises": [0]
        }
    ]
}

print("=========================================================")
print("RUNNING ALL TRACK 1 TEST CASES AGAINST COMPETITION API")
print("=========================================================")

passed_count = 0
total_count = 0

for category, cases in test_cases.items():
    print(f"\n--- Category: {category} ---")
    for tc in cases:
        total_count += 1
        print(f"\nRunning test: {tc['query_id']}")
        
        payload = {
            "query_id": tc["query_id"],
            "type": tc["type"],
            "query": tc["query"],
            "premises": tc["premises"],
            "options": tc["options"]
        }
        
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                
                model_response = res_json[0] if isinstance(res_json, list) else res_json
                ans = model_response.get("answer")
                prems = model_response.get("premises_used", [])
                
                print(f"  Answer: {repr(ans)}")
                print(f"  Premises Used: {prems}")
                
                ans_ok = False
                if tc["expected_answer"].lower() in str(ans).lower() or str(ans).lower() in tc["expected_answer"].lower():
                    ans_ok = True
                
                prems_ok = (sorted(prems) == sorted(tc["expected_premises"]))
                
                if ans_ok and prems_ok:
                    status = "✅ PASS"
                    passed_count += 1
                else:
                    status = "❌ FAIL"
                    
                print(f"  Status: {status}")
                if not ans_ok:
                    print(f"    Warning: Expected answer near {repr(tc['expected_answer'])}, got {repr(ans)}")
                if not prems_ok:
                    print(f"    Warning: Expected premises {tc['expected_premises']}, got {prems}")
                    
        except Exception as e:
            print(f"❌ HTTP/API Request failed: {e}")

print("\n=========================================================")
print(f"COMPLETED. Passed {passed_count}/{total_count} test cases.")
print("=========================================================")
