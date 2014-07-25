import sys
import os
import argparse
import json

from datetime import datetime

class Participant(object):
    def __init__(self, gaia_id, chat_id, name):
        self.name = name
        self.gaia_id = gaia_id
        self.chat_id = chat_id

    def get_id(self):
        return self.gaia_id

    def get_name(self):
        return self.name

    def __unicode__(self):
        if self.get_name() is None:
            return self.get_id()
        else:
            return self.get_name()

class ParticipantList(object):
    def __init__(self):
        self.p_list = {}
        self.current_iter = 0
        self.max_iter = 0

    def add(self, p):
        self.p_list[p.get_id()] = p
        return self.p_list

    def get_by_id(self, id):
        try:
            return self.p_list[id]
        except:
            return None

    def __iter__(self):
        self.current_iter = 0
        self.max_iter = len(self.p_list)-1
        return self

    def next(self):
        if self.current_iter > self.max_iter:
            raise StopIteration
        else:
            self.current_iter += 1
            return self.p_list.values()[self.current_iter-1]

    def __unicode__(self):
        return ", ".join([unicode(p) for p in self.p_list.values()])

class Event(object):
    def __init__(self, event_id, sender_id, timestamp, message):
        self.event_id = event_id
        self.sender_id = sender_id
        self.timestamp = timestamp
        self.message = message

    def get_id(self):
        return self.event_id

    def get_sender_id(self):
        return self.sender_id

    def get_timestamp(self):
        return self.timestamp

    def get_message(self):
        return self.message

    def get_formatted_message(self):
        # formatted message (the messages are joined by a space).
        return " ".join(self.message)

class EventList(object):
    def __init__(self):
        self.event_list = {}
        self.current_iter = 0
        self.max_iter = 0

    def add(self, e):
        self.event_list[e.get_id()] = e
        return self.event_list

    def get_by_id(self, id):
        try:
            return self.event_list[id]
        except:
            return None

    def __iter__(self):
        self.current_iter = 0
        self.max_iter = len(self.event_list)-1
        return self

    def next(self):
        if self.current_iter > self.max_iter:
            raise StopIteration
        else:
            self.current_iter += 1
            return self.event_list.values()[self.current_iter-1]

class Conversation(object):
    def __init__(self, conversation_id, participants, events):
        self.conversation_id = conversation_id
        self.participants = participants
        self.events = events

    def get_id(self):
        return self.conversation_id

    def get_participants(self):
        return self.participants

    def get_events(self):
        return sorted(self.events, key=lambda event: event.get_timestamp())

    def get_events_unsorted(self):
        return self.events

class HangoutsReader(object):
    def __init__(self, logfile, conversation_id=None):
        self.filename = self.validate_file(logfile)
        self.conversation_id = conversation_id

        # parse the json file
        self.parse_json_file(logfile)

    def parse_json_file(self, filename):
        with open(filename) as json_data:
            data = json.load(json_data)

        for conversation in data["conversation_state"]:
            c = self.extract_conversation_data(conversation)
            if self.conversation_id is None:
                self.print_("conversation id: %s, participants: %s" % (c.get_id(), unicode(c.get_participants())))
            elif c.get_id() == self.conversation_id:
                self.print_conversation(c)

    def print_conversation(self, conversation):
        participants = conversation.get_participants()
        for event in conversation.get_events():
            self.print_(u"[{timestamp}] {author}: {message}".format(
                        timestamp = datetime.fromtimestamp(long(long(event.get_timestamp())/10**6.)),
                        author = participants.get_by_id(event.get_sender_id()).get_name(),
                        message = event.get_formatted_message(),
                    ))

    def extract_conversation_data(self, conversation):
        try:
            # note the initial timestamp of this conversation
            conversation_id = conversation["conversation_id"]["id"]

            # find out the participants
            participant_list = ParticipantList()
            for participant in conversation["conversation_state"]["conversation"]["participant_data"]:
                gaia_id = participant["id"]["gaia_id"]
                chat_id = participant["id"]["chat_id"]
                try:
                    name = participant["fallback_name"]
                except KeyError:
                    name = None
                p = Participant(gaia_id, chat_id, name)
                participant_list.add(p)

            event_list = EventList()

            for event in conversation["conversation_state"]["event"]:
                event_id = event["event_id"]
                sender_id = event["sender_id"] # has dict values "gaia_id" and "chat_id"
                timestamp = event["timestamp"]
                text = list()
                try:
                    message_content = event["chat_message"]["message_content"]
                    for segment in message_content["segment"]:
                        if segment["type"].lower() in ("TEXT".lower(), "LINK".lower()):
                            text.append(segment["text"])
                    try:
                        for attachment in message_content["attachment"]:
                            # if there is a Google+ photo attachment we append the URL
                            if attachment["embed_item"]["type"][0].lower() == "PLUS_PHOTO".lower():
                                text.append(attachment["embed_item"]["embeds.PlusPhoto.plus_photo"]["url"])
                    except KeyError:
                        pass # may happen when there is no (compatible) attachment
                except KeyError:
                    continue # that's okay
                # finally add the event to the event list
                event_list.add(Event(event_id, sender_id["gaia_id"], timestamp, text))
        except KeyError:
            raise RuntimeError("The conversation data could not be extracted.")
        return Conversation(conversation_id, participant_list, event_list)

    def validate_file(self, filename):
        if not os.path.isfile(filename):
            raise ValueError("The given file is not valid.")
        return filename

    def print_(self, message):
        print unicode(message).encode('utf8')

def main(argv):
    parser = argparse.ArgumentParser(description='Commandline python script that allows reading Google Hangouts logfiles.')

    parser.add_argument('logfile', type=str, help='filename of the logfile')
    parser.add_argument('--conversation-id', '-c', type=str, help='shows the conversation with given id')

    args = parser.parse_args()

    hr = HangoutsReader(args.logfile, conversation_id=args.conversation_id)


if __name__ == "__main__":
    main(sys.argv)
