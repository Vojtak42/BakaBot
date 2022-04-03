import asyncio
import copy
import datetime
import json
import re

import discord
from bs4 import BeautifulSoup
from utils.utils import get_sec, login, read_db, write_db


class Grades:
    def __init__(self, grades):
        self.grades = grades

    class Grade:
        def __init__(
            self, id: str, caption: str, subject: str, weight: int, note: str, date: list, grade: float or int
        ):
            self.id = id
            self.caption = caption
            self.subject = subject
            self.weight = weight
            self.note = note
            self.date = date
            self.grade = grade

        def grade_string(self):
            if self.grade % 1 != 0:
                return str(int(self.grade)) + "-"
            else:
                return str(int(self.grade))

        def show(self, grades):
            # Creation of the embed
            embed = discord.Embed()

            # Subject
            embed.set_author(name=Grades.SUBJECTS.get(self.subject))

            # Grade
            embed.title = self.grade_string()

            # Captions and notes into the same field (Same thing really)
            captionsNotes = ""
            if self.caption:
                captionsNotes += "\n" + self.caption
            if self.note:
                captionsNotes += "\n" + self.note

            # Weight
            embed.description = f"Váha: {self.weight}{captionsNotes}"

            # Current and future average
            content = f"Průměr z {self.subject}: {Grades.round_average((grades).by_subject(self.subject).average())}"
            embed.add_field(name="\u200b", value=content, inline=False)

            # Date
            embed.timestamp = datetime.datetime(*self.date)

            # Color of the embed from green (good) to red (bad) determining how bad the grade is
            green = int(255 / 4 * (self.grade - 1))
            red = int(255 - 255 / 4 * (self.grade - 1))
            embed.color = discord.Color.from_rgb(green, red, 0)

            # Returns the embed
            return embed

    @staticmethod
    def empty_grade(subject=None, weight=1, grade=1, date=None, id=None):
        """Makes a Grade object with as little parameters as possible"""
        return Grades.Grade(id, None, subject, weight, None, date, grade)

    def by_subject(self, subject):
        """Returns only Grades with the wanted subject"""
        gradesBySubject = []
        for grade in self.grades:
            if grade.subject == subject:
                gradesBySubject.append(grade)
        return Grades(gradesBySubject)

    def average(self):
        """Returns the average grade from the self Grades\n
        (Calculated with weights in mind)"""
        # Total amount of grades
        gradesTotal = 0
        # Total amount of grades included with their weights
        gradesWeightsTotal = 0

        for grade in self.grades:
            gradesTotal += grade.weight
            gradesWeightsTotal += grade.grade * grade.weight
        # Rounds the average and returns it
        average = self.round_average(gradesWeightsTotal / gradesTotal)
        return average

    def future_average(self, grade):
        """Returns the possible future average with the given grade"""
        # Copyies itself to work with a Grades object without damaging the original
        grades = copy.deepcopy(self)

        # Appends the grade, calculates the average and removes it
        grades.grades.append(grade)

        # Returns averages
        return grades.average()

    @staticmethod
    def round_average(average: float):
        """Rounds the average to some normal nice looking finite number"""
        if average % 1 == 0:
            return int(average)
        if average % 10 == 0:
            return int(average * 10) / 10
        else:
            return int(average * 100) / 100

    @staticmethod
    def json_loads(jsonstring: str):
        """Loads a Schedule object from JSON"""
        dictGrades = json.loads(jsonstring)
        grades = Grades([])
        for grade in dictGrades["grades"]:
            grades.grades.append(
                Grades.Grade(
                    grade["id"],
                    grade["caption"],
                    grade["subject"],
                    grade["weight"],
                    grade["note"],
                    grade["date"],
                    grade["grade"],
                )
            )
        return grades

    @staticmethod
    def json_dumps(grades):
        """Makes a JSON from Schedule object"""
        output = '{"grades": ['
        for grades in grades.grades:
            output = output + json.dumps(grades.__dict__) + ", "
        output = output[:-2] + "]}"

        return output

    @staticmethod
    async def db_grades():
        """Gets Grades object from the database"""
        grades = read_db("grades")
        if not grades:
            grades = await Grades.get_grades()
            write_db("grades", Grades.json_dumps(grades))
        return Grades.json_loads(grades)

    # Constants for all subjects with their short and long form
    SUBJECTS = {
        "Inf": "Informatika a výpočetní technika",
        "EvV": "Estetická výchova - výtvarná",
        "EvH": "Estetická výchova - hudební",
        "Zsv": "Základy společenských věd",
        "Čj": "Český jazyk a literatura",
        "Fj": "Jazyk francouzský",
        "Tv": "Tělesná výchova",
        "Aj": "Jazyk anglický",
        "M": "Matematika",
        "Bi": "Biologie",
        "Fy": "Fyzika",
        "Ch": "Chemie",
        "D": "Dějepis",
        "Z": "Zeměpis",
    }
    SUBJECTS_REVERSED = {}
    for key, value in zip(SUBJECTS.keys(), SUBJECTS.values()):
        SUBJECTS_REVERSED.update({value: key})
    SUBJECTS_LOWER = {}
    for key in SUBJECTS.keys():
        SUBJECTS_LOWER.update({key.lower(): key})

    @staticmethod
    async def get_grades():
        """Returns a Grades object with the exctracted information from the server"""
        # Gets response from the server
        session = await login()
        url = "https://bakalari.ceskolipska.cz/next/prubzna.aspx?s=chrono"
        response = await session.get(url)
        # Making an BS html parser object from the response
        html = BeautifulSoup(await response.text(), "html.parser")
        await session.close()

        # Web scraping the response
        data = html.find("div", {"id": "cphmain_DivByTime"}).script.text
        data = re.findall("\[\{.*?(?=;)", data)[0]
        # Creates an empty Grades object
        grades = Grades([])
        # Parses the data into a dicture
        dictData = json.loads(data)
        for row in dictData:
            # Reads the data from the dicture (Still need to properly parse it)
            caption = row["caption"]
            id = row["id"]
            subject = row["nazev"]
            weight = row["vaha"]
            note = row["poznamkakzobrazeni"]
            date = row["udel_datum"]
            grade = row["MarkText"]

            # If a there is a caption parse it else None
            if caption != "":
                caption = caption.replace(" <br>", "")
            else:
                caption = None
            # Gets a short name for the subject
            subject = Grades.SUBJECTS_REVERSED[subject]
            # Gets an int of the weight
            weight = int(weight)
            # If a there is a note parse it else None
            if note != "":
                note = note.replace(" <br>", "")
            else:
                note = None
            # Parses the date into list of [Year, Month, Day]
            date = list(reversed([int(date_x) for date_x in date.split(".")]))
            # Parses the grade an int or a float because of this "-" symbol
            if "-" in grade:
                grade = int(grade.replace("-", "")) + 0.5
            else:
                grade = int(grade)

            # Appends the grade to grades
            grades.grades.append(Grades.Grade(id, caption, subject, weight, note, date, grade))
        # Returns full Grades object
        return grades

    # Variable to store running timers
    message_remove_timers = []

    PREDICTOR_EMOJI = "📊"

    @staticmethod
    async def create_predection(message: discord.message.Message, client: discord.Client):
        from core.predictor import Predictor

        """Generates a predict message with the current subject"""
        # Subject
        subject = Grades.SUBJECTS_REVERSED.get(message.embeds[0].author.name)

        # Removes the reacted emoji from the message
        await Grades.delete_grade_reaction(message, Grades.PREDICTOR_EMOJI, 0)

        # Sends the grade predictor
        predictorMessage = await Predictor.predict_embed(subject, message.channel, client)

    @staticmethod
    async def delete_grade_reaction(message: discord.Message, emoji: discord.emoji, delay: int):
        """Deletes the reaction from the message after some delay"""
        # Puts the message into the timer variable
        Grades.message_remove_timers.append([message.id, get_sec() + delay])
        # Sleeps for the time of the delay
        await asyncio.sleep(delay)

        for timer in Grades.message_remove_timers:
            # Checks if the timer is still active
            if message.id == timer[0]:
                try:
                    # Removes the reaction
                    await message.clear_reaction(emoji)
                    toRemoveMessages = read_db("gradesMessages")
                    Grades.message_remove_timers.remove(timer)
                    toRemoveMessages.remove([message.id, message.channel.id])
                    write_db("gradesMessages", toRemoveMessages)
                except:
                    pass

    @staticmethod
    async def detect_changes(client: discord.Client):
        """Detects changes in grades and sends them to discord"""
        # Finds and returns the actual changes
        def find_changes(gradesOld: Grades, gradesNew: Grades):
            newGrades = []
            oldIDs = [grade.id for grade in gradesOld.grades]
            for grade in gradesNew.grades:
                # New unrecognized ID
                if grade.id not in oldIDs:
                    newGrades.append(grade)
            return newGrades

        # Discord message with the information about the changes
        async def changed_message(changed: list, grades: Grades, client: discord.Client):
            channel = read_db("channelGrades")
            for grade in changed:
                # Makes the embed
                embed = grade.show(grades)

                # Sends the embed
                message = await client.get_channel(channel).send(embed=embed)

                # Saves the reaction to be removed later
                messages = read_db("gradesMessages")
                if messages:
                    messages = list(messages)
                else:
                    messages = []
                messages.append([message.id, message.channel.id])
                write_db("gradesMessages", messages)
                client.cached_messages_react.append(message)
                # Adds the reaction emoji
                await message.add_reaction(Grades.PREDICTOR_EMOJI)
                # Removes the emoji after 1.5 hours of inactivity
                asyncio.ensure_future(Grades.delete_grade_reaction(message, Grades.PREDICTOR_EMOJI, 5400))

        # The main detection code
        # Gets the new Grade object
        gradesNew = await Grades.get_grades()
        # Gets the old Grades object
        gradesOld = await Grades.db_grades()

        # Detects any changes and sends the message and saves the schedule if needed
        changed = find_changes(gradesOld, gradesNew)
        if changed:
            await changed_message(changed, gradesNew, client)
            write_db("grades", Grades.json_dumps(gradesNew))

    @staticmethod
    async def start_detecting_changes(interval: int, client: discord.Client):
        """Starts an infinite loop for checking changes in the grades"""
        while True:
            await Grades.detect_changes(client)
            await asyncio.sleep(interval)