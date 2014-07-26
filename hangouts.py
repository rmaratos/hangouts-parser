import sys
import os
import argparse
import json

from datetime import datetime
from operator import attrgetter

def unicode_print(s):
    print unicode(s).encode('utf8')

class Event(object):
    def __init__(self, sender, timestamp, message):
        self.sender = sender
        self.timestamp = datetime.fromtimestamp(long(long(timestamp)/10**6.))
        self.message = " ".join(message)

    def __unicode__(self):
        return u"[{timestamp}] {author}: {message}".format(
                        timestamp = self.timestamp,
                        author = self.sender,
                        message = self.message)

class Conversation(object):
    def __init__(self, raw_data):
        self.data = raw_data
        self.parse_participants()

    def get_events(self):
        return sorted(self.events, key=attrgetter("timestamp"))

    def get_participants(self):
        return ", ".join(self.participants.values())

    def rename_participants(self):
        while True:
            user_input = raw_input("Would you like to rename any participants? (y/n): ")
            if user_input not in "yn":
                print "I didn't get that, please type y or n"
            elif user_input == "y":
                new_participants = {}
                for p_id, participant in self.participants.items():
                    user_input = raw_input("Rename {} (leave blank for no change): ".format(participant))
                    if user_input:
                        new_participants[p_id] = user_input
                    else:
                        new_participants[p_id] = participant
                for p_id, old in self.participants.items():
                    new = new_participants[p_id]
                    if new != old:
                        print "{} -> {}".format(old, new)
                user_input = raw_input("Confirm changes. (y/n): ")
                if user_input not in "yn":
                    print "I didn't get that, please type y or n"
                elif user_input == "y":
                    self.participants = new_participants
                    return
            elif user_input == "n":
                return


    def parse_participants(self):
        participants = {}
        for participant in self.data["conversation_state"]["conversation"]["participant_data"]:
            gaia_id = participant["id"]["gaia_id"]
            name = participant.get("fallback_name")
            participants[gaia_id] = name
        self.participants = participants

    def parse_events(self):
        try:
            self.events = []
            for event in self.data["conversation_state"]["event"]:
                gaia_id = event["sender_id"]["gaia_id"]
                sender = self.participants[gaia_id]

                timestamp = event["timestamp"]

                message = []
                chat_message = event.get("chat_message")
                if chat_message:
                    message_content = chat_message["message_content"]

                    for segment in message_content.get("segment", []):
                        if segment["type"] in ("TEXT", "LINK"):
                            message.append(segment["text"])

                    for attachment in message_content.get("attachment", []):
                        # if there is a Google+ photo attachment we append the URL
                        if attachment["embed_item"]["type"][0] == "PLUS_PHOTO":
                            message.append(attachment["embed_item"]["embeds.PlusPhoto.plus_photo"]["url"])
                # finally add the event to the event list
                self.events.append(Event(sender, timestamp, message))
        except KeyError as e:
            raise RuntimeError("The conversation data could not be extracted: {}".format(e))

    def print_events(self):
        for event in self.get_events():
            unicode_print(event)

    def write(self):
        user_input = raw_input("Choose path for output:")
        path = os.path.expanduser(user_input)
        if os.path.isfile(path):
            print "Sorry, file already exists."
        else:
            with open(path, "w") as f:
                for event in self.get_events():
                    f.write(unicode(event).encode('utf8') + "\n")
    def __unicode__(self):
        return self.get_participants()

class HangoutsReader(object):
    def __init__(self, logfile):
        self.filename = self.validate_file(logfile)
        self.parse_json_file(logfile)
        self.user_loop()

    def user_loop(self):
        while True:
            index = self.choose_conversation()
            conversation = self.conversations[index]
            conversation.rename_participants()
            conversation.parse_events()
            self.print_or_write(conversation)

    def print_or_write(self, conversation):
        while True:
            user_input = raw_input("Print or write to file? (print/write)")
            if user_input == "print":
                conversation.print_events()
                return
            elif user_input == "write":
                conversation.write()
                return
            else:
                print "Invalid."

    def choose_conversation(self):
        self.print_conversations()
        while True:
            user_input = raw_input("Select conversation: ")
            if user_input == "quit":
                sys.exit()
            try:
                index = int(user_input)
            except ValueError:
                print "Please enter a number."
            else:
                if 0 <= index < len(self.conversations):
                    return index
                else:
                    print "Please enter a valid index between 0 and {}.".format(
                        len(self.conversations) - 1)

    def print_conversations(self):
        print "Conversations:"
        for i, conversation in enumerate(self.conversations):
            print u"{}: {}".format(i, conversation)

    def parse_json_file(self, filename):
        with open(filename) as json_data:
            data = json.load(json_data)

        self.conversations = [Conversation(d) for d in data["conversation_state"]]

    def validate_file(self, filename):
        if not os.path.isfile(filename):
            raise ValueError("The given file is not valid.")
        return filename

def main(argv):
    parser = argparse.ArgumentParser(description='Commandline python script that allows reading Google Hangouts logfiles.')
    parser.add_argument('logfile', type=str, help='filename of the logfile')
    args = parser.parse_args()

    HangoutsReader(args.logfile)

if __name__ == "__main__":
    main(sys.argv)
