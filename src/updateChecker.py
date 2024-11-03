from os import path
import requests
from datetime import datetime
from threading import Thread
from time import localtime

#Get the date of when the specified file was last modified
def getModifiedDate(fileDir):
    try:
         modifiedDate = path.getmtime(fileDir)
         timezoneOffset = localtime().tm_gmtoff
         return modifiedDate - timezoneOffset
    except:
        return -1

#Get date of when the last commit was made
def getDataFromLatestCommit(repoURL):
    apiURL = repoURL.replace("https://github.com/", "https://api.github.com/repos/")
    url = f"{apiURL}/branches/master"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            lastCommitDate = data['commit']['commit']['committer']['date']
            lastCommmitSHA = data['commit']['commit']['tree']['sha']

            dateTimeObject = datetime.strptime(lastCommitDate, "%Y-%m-%dT%H:%M:%SZ")
            unixTimestamp = float(dateTimeObject.timestamp())
            return unixTimestamp, lastCommmitSHA
        else:
            return -1, -1

    except:
        return -1, -1

#Compares modified date and commit date to see if a new update is available
def isUpdateRequired(fileCheck, repoURL, updateAction):
    def mainCheck():
        modifiedDate = getModifiedDate(fileCheck)
        latestCommitDate, latestCommitSHA = getDataFromLatestCommit(repoURL)

        if not ((modifiedDate < 0) or (latestCommitDate < 0)) and (modifiedDate < latestCommitDate):
            updateAction(latestCommitSHA)

    mainThread = Thread(target = mainCheck)
    mainThread.start()
