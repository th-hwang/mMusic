import getpass

import argparse

import re
import os
import shutil
import subprocess

import datetime
import sys

from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from bs4 import BeautifulSoup


def validStr(string):
    logger.debug(
        "Checking the validation of string. Meta character is not allowed")

    if (len(re.findall(r"[-=#/?:;$()^%&']", string)) != 0):
        print("Meta Character is not allowed in your string")
        return False
    elif (len(string) < 5):
        print("Your string is too short. It should be >5")
        return False
    else:
        return True


def getUserAccount(msg="", userID=""):

    if (msg != ""):
        print(msg)

    while True:
        if (userID == ""):
            userID = input("login ID: ")
        if not (validStr(userID)):
            userID = ""
            continue

        pwd1 = getpass.getpass(userID + "'s password: ")
        if not (validStr(pwd1)):
            continue

        pwd2 = getpass.getpass("retype your password: ")
        if not (validStr(pwd2)):
            continue

        if (pwd1 == pwd2):
            break
        print("The current password don't match with the previous password")

    return {'uid': userID, 'passwd': pwd1, 'privilege': False}


def addUser(dbCon, dbName, userTB, homeDir, userInfo):
    logger.debug(
        "Adding user account [%s] into the user table [%s] in the database [%s]", userInfo['uid'], userTB, dbName)

    if (existUser(dbCon, dbName, userTB, userInfo)):
        logger.error(
            "%s cannot be available because it already exists", userInfo['uid'])
        return False
    elif (isFirstUser(dbCon, dbName, userTB)):
        print("{uid} is the first one. All privilege is allowed.".format(
            uid=userInfo['uid']))
        userInfo['privilege'] = True
        executeFlag = True
    else:
        userInfo['privilege'] = False
        executeFlag = isAdmin(dbCon, dbName, userTB)
        if not executeFlag:
            logger.error("Admin's login ID or password is incorrect")

    if (executeFlag):
        makeUserAccount(dbCon, dbName, userTB, userInfo)
        makeMusicTB(dbCon, dbName, userInfo['uid'])
        makeUserDir(homeDir+userInfo['uid'])
        return True
    else:
        return False


def isAdmin(dbCon, dbName, userTB):
    logger.debug(
        "Checking if you are the admin. The admin who has privilege can add or delete account ")
    trial = 1  # trial should be < maxtrial
    maxtrial = 2

    while True:
        adminInfo = getUserAccount(
            "To do your request we need to know admin\'s login id and password")
        adminInfo['privilege'] = True

        if (checkUser(dbCon, dbName, userTB, adminInfo)):
            return True
        else:
            if (trial > maxtrial):
                return False
            print("Wrong admin login id or password. Try it again. {tr} more trial left".format(
                tr=maxtrial - trial))
            trial += 1


def makeUserDir(strDir):
    if not os.access(strDir, os.F_OK):
        try:
            return os.makedirs(strDir, 0o775)
        except:
            logger.error("Error in makeUserDir().")
            return False


def removeUser(dbCon, dbName, userTB, homeDir, userInfo):
    logger.debug(
        "Deleting user account [%s] from the user table [%s] in the database [%s]", userInfo['uid'], userTB, dbName)

    if (existUser(dbCon, dbName, userTB, userInfo)):
        if (isAdmin(dbCon, dbName, userTB)):
            deleteUserAccount(dbCon, dbName, userTB, userInfo)
            deleteMusicTable(dbCon, dbName, userInfo['uid'])
            deleteUserDir(homeDir+userInfo['uid'])
            return True
        else:
            logger.error("Admin's login ID or password is incorrect")
            return False

    else:
        logger.error(
            "%s cannot be deleted because it doesnot exists in the user table [%s] in the database [%s] ", userInfo['uid'], userTB, dbName)
        return False


def deleteUserDir(strDir):
    if os.access(strDir, os.F_OK):
        try:
            return shutil.rmtree(strDir)
        except:
            logger.error("Error in deleteUserDir().")
            raise
# Handling Music Files


def addMusic(dbCon, dbName, homeDir, userInfo, musicList):
    logger.debug("Adding musics list ---")

    updateMusicDB(dbCon, dbName, userInfo['uid'], [
                  os.path.join(homeDir, userInfo['uid']), ])
    insertMusicDB(dbCon, dbName, userInfo['uid'], os.path.join(
        homeDir, userInfo['uid']), musicList)

    return True


def insertMusicDB(dbCon, dbName, musicTB, dstDir, musicList):
    logger.info("inserting music information into database .....")

    for ff in makeMusicList(musicList):
        tagToUTF8(ff)
        tag = getTag(ff)

        if (isInMusicDB_ArtistTitle(dbCon, dbName, musicTB, tag)):
            # ----
            logger.info(
                "[Skip] {fn} already exists ................. [Skip]".format(fn=ff))
        else:
            logger.info(
                "[Move] {fn} is moving to {dr} ............... [Ok]".format(fn=ff, dr=dstDir))

            insertMusicRecord(dbCon, dbName, musicTB, tag)
            shutil.move(ff, dstDir)


def makeMusicList(musicList):
    result = []

    for ff in musicList:
        if(os.path.isdir(ff)):
            logger.info("%s is directory. Walk into the directory " % ff)
            if os.listdir(ff):
                for (path, dirs, files) in os.walk(ff):
                    for ff2 in files:
                        fName = os.path.abspath(os.path.join(path, ff2))
                        if (isMusic(fName)):
                            result.append(fName)
                        else:
                            logger.info("[Skip] " + fName +
                                        " is not music file. ..... [Skip]")
            else:
                logger.info("[Skip] " + ff + " is empty .......... [Skip]")

        else:
            if (isMusic(ff)):
                result.append(os.path.abspath(ff))
            else:
                logger.info("[Skip] " + ff +
                            " is not music file. ..... [Skip]")

    return result


def isMusic(fName):
    slist = ['id3', 'oggs', 'flac']
    isMusicFlag = False
    with open(fName, 'rb') as ff:
        fhead = ff.read(4)
        isMusicFlag = (fhead[0:3].lower() in slist) or (fhead.lower() in slist)
    return isMusicFlag


def tagToUTF8(src):
    p = subprocess.Popen(["/usr/local/bin/mid3iconv", "-e",
                         "cp949", src], stdout=subprocess.PIPE).stdout
    result = p.read().strip()
    p.close()
    return result


def getTag(fName):
    logger.debug("Parcing Tag")

    tag = mutagen.File(fName)

    result = {}
    result['title'] = parsingSong(tag, 'TIT2')
    result['artist'] = parsingSong(tag, 'TPE1')
    result['album'] = parsingSong(tag, 'TALB')
    result['sdate'] = parsingSong(tag, 'TDRC')
    result['genre'] = parsingSong(tag, 'TCON')
    # result['lyric'] 	= parsingSong(tag,'USLT::kor')
    # result['coverimg'] 	= parsingSong(tag,'APIC:')
    result['filename'] = os.path.basename(
        fName).decode(sys.stdin.encoding).encode('utf8')
    result['currentrank'] = 9999
    result['favor'] = 0
    result['deleteflag'] = False

    return result


def parsingSong(mutagenObj, frameID):
    # the TAG of cover_image sometimes chages "APIC:" to the other, such as "APIC:SYK"
    # to indicate tag of cover image, compare frameID with each mutagenObj.keys()
    for mtg in mutagenObj.keys():
        if 'APIC:' in frameID and frameID in mtg:  # processing cover image
            return mutagenObj[mtg].data
        elif 'USLT' in frameID and frameID in mtg:  # process lyric
            return str(mutagenObj[mtg].text, 'utf8')
        elif 'TDRC' in frameID and frameID in mtg:
            strtmp = mutagenObj[mtg].text[0].encode('iso-8859-1')
            if len(strtmp) <= 4:
                strtmp = datetime.datetime.now().strftime("%y%m%d")
            return str(strtmp.replace("-", ""), 'utf8')
        elif frameID in mtg:
            return str(mutagenObj[frameID].text[0], 'utf8')


def updateMusicDB(dbCon, dbName, musicTB, musicDir):  # musicDir should be list
    logger.info("Updating Database .....")

    setDeleteFlag(dbCon, dbName, musicTB)

    for ff in makeMusicList(musicDir):
        tag = getTag(ff)
        if (isInMusicDB_ArtistTitle(dbCon, dbName, musicTB, tag)):
            unsetDeleteFlag(dbCon, dbName, musicTB, tag)
            increaseFavor(dbCon, dbName, musicTB, tag)

    return deleteMusicRecord(dbCon, dbName, musicTB)


def setDeleteFlag(dbCon, dbName, musicTB):
    logger.debug("Setting delete-flag of all music to on")
    sql = """update {db}.{tb} set deleteflag=True"""
    sql = sql.format(db=dbName, tb=musicTB)

    return sendQuery(dbCon, sql, mode="DML")


def unsetDeleteFlag(dbCon, dbName, musicTB, tag):
    logger.debug("Setting delete-flag of all music to off")
    sql = """update {db}.{tb} set deleteflag=False where title = "{ti}" and artist="{ar}" """
    sql = sql.format(db=dbName, tb=musicTB, ti=simplify(
        tag['title']), ar=simplify(tag['artist']))

    return sendQuery(dbCon, sql, mode="DML")


def increaseFavor(dbCon, dbName, musicTB, tag):
    logger.debug("Increasing favorite number of music")
    sql = """update {db}.{tb} set favor=favor+1 where title = "{ti}" and artist="{ar}" """
    sql = sql.format(db=dbName, tb=musicTB, ti=simplify(
        tag['title']), ar=simplify(tag['artist']))

    return sendQuery(dbCon, sql, mode="DML")


def deleteMusicRecord(dbCon, dbName, musicTB):
    logger.debug("Deleting music records having on delete-flag ")
    sql = """delete from {db}.{tb} where deleteflag=True"""
    sql = sql.format(db=dbName, tb=musicTB)

    return sendQuery(dbCon, sql, mode="DML")


def updateRank(dbCon, dbName, musicTB, phantomjs_path, th=0.5):  # if matchingRate >50%
    logger.debug(
        "Crawling from Melon top 100 chart. And then update current rank")

    sql = """select idmusic, title, artist, album from {db}.{tb}"""
    sql = sql.format(db=dbName, tb=musicTB)
    sList = list(sendQuery(dbCon, sql))

    setCurrentRank(dbCon, dbName, musicTB, 101)  # default rank 101
    musicRank = getRank(phantomjs_path)

    for (idMusic, title, artist, album) in sList:
        maxMR = 0.0
        for idx, ff in enumerate(musicRank):
            # data from database is unicode, crawling data is utf8
            logger.debug("src: {id}/{ln} || {ti} || {ar} || {al}".format(id=idMusic, ln=len(
                sList), ti=title.encode('utf8'), ar=artist.encode('utf8'), al=album.encode('utf8')))
            logger.debug("tgt: {id}/{ln} || {ti} || {ar} || {al}".format(
                id=idx+1, ln=len(musicRank), ti=ff['title'], ar=ff['artist'], al=ff['album']))

            # the best case is with only title and artist , without
            # current matching rate
            curMR = matchingRate(
                title+artist, str(ff['title']+ff['artist'], 'utf8'))
            # curMR = matchingRate(title+artist+album,unicode(ff['title']+ff['artist']+ff['album'],'utf8')) # current matching rate
            # curMR = matchingRate(title, unicode(ff['title'],'utf8')) +  matchingRate(artist, unicode(ff['artist'],'utf8')) + matchingRate(album, unicode(ff['album'],'utf8'))

            logger.debug("thMr : " + str(th)+" curMR : " +
                         str(curMR)+" sList : " + str(len(musicRank)))

            if curMR >= maxMR:
                maxMR = curMR
                maxIdMusic = idMusic
                maxRank = ff['rank']
                maxTitle = ff['title']
                maxArtist = ff['artist']
                maxAlbum = ff['album']
            else:
                continue

        if (maxMR >= th):

            logger.info("[DB]: title = '{ti}' || artist = '{ar}' || album = '{al}' || num/total {id}/{ln} ||"
                        .format(id=idMusic, ln=len(sList), ti=title.encode('utf8'), ar=artist.encode('utf8'), al=album.encode('utf8')))
            logger.info("[CH]: title = '{ti}' || artist = '{ar}' || album = '{al}' || rank = {ra} || MR = {mr} || {ln} musicRanks are left ||"
                        .format(mr=maxMR, ln=len(musicRank), ra=maxRank, ti=maxTitle, ar=maxArtist, al=maxAlbum))

            insertRank(dbCon, dbName, musicTB, maxIdMusic, maxRank)
            musicRank.remove({'rank': maxRank, 'title': maxTitle,
                             'artist': maxArtist, 'album': maxAlbum})
    # remained musicRank
    # print ("--------------------------------------")
    # for idx, ff in enumerate(musicRank):
    #     logger.info(" [{nu}] title = '{ti}' || artist = '{ar}' || album = '{al}' || rank = {ra}"
    #             .format(nu=idx, ra=ff['rank'], ti= ff['title'], ar=ff['artist'], al=ff['album']))


def setCurrentRank(dbCon, dbName, musicTB, defaultRank):
    logger.debug(
        "Set current rank to default rank {dr}".format(dr=defaultRank))

    sql = """update {db}.{tb} set currentrank = {ra}"""
    sql = sql.format(db=dbName, tb=musicTB, ra=defaultRank)

    return sendQuery(dbCon, sql, mode="DML")


def getRank(phantomjs_path):
    logger.info("Connecting Melon Top 100 chart ..... ")

    dcap = dict(DesiredCapabilities.PHANTOMJS)
    dcap["phantomjs.page.settings.userAgent"] = \
        ("Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; " +
         ".NET CLR 3.0.30729; Media Center PC 6.0; MAAU; .NET4.0C; .NET4.0E; InfoPath.2; rv:11.0) like Gecko")

    driver = webdriver.PhantomJS(executable_path=phantomjs_path,
                                 desired_capabilities=dcap, service_log_path='/tmp/ghostdriver.log')
    driver.get("http://www.melon.com/chart/index.htm")

    # driver.save_screenshot("/Users/taehyunghwang/Works/test.png")
    # print (driver.page_source)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    logger.info("Parsing Melon Top 100 chart ..... ")

    result = []

    for tName in ('lst50', 'lst100'):
        for row in soup.find_all("tr", {"class": tName}):
            tmp = {'rank': row.find("span", {"class": "rank"}).get_text().encode('utf8'),
                   'title': row.find("div", {"class": "ellipsis rank01"}).find("a").get_text().encode('utf8'),
                   'artist': row.find("div", {"class": "ellipsis rank02"}).find("a").get_text().encode('utf8'),
                   'album': row.find("div", {"class": "ellipsis rank03"}).find("a").get_text().encode('utf8')}
            result.append(tmp)

    return result


def matchingRate(src, tgt):
    logger.debug("Comparing simplified src {sc} and simplified tgt {tg}".format(
        sc=simplify(src).encode('utf8'), tg=simplify(tgt).encode('utf8')))
    cnt = 0
    step = 2
    simpSrc = simplify(src)
    simpTgt = simplify(tgt)

    logger.debug("[SRC] : title = {sc}".format(
        sc=simplify(src).encode('utf8')))
    logger.debug("[TGT] : title = {tg}".format(
        tg=simplify(tgt).encode('utf8')))

    for i in range(0, len(simpTgt), step):

        if simpTgt[i:i+step] in simpSrc:
            cnt += 1
            logger.debug("simpTgt[i:i+step]  - " + simpTgt[i:i+step] + " : True, Count : "+str(
                cnt)+"/"+str(len(simpTgt)/step + (0 if len(simpTgt) % 2 == 0 else 1)))
        else:
            logger.debug("simpTgt[i:i+step]  - " +
                         simpTgt[i:i+step] + " : False")
            continue

    return float(cnt)/float(len(simpTgt)/step + (0 if len(simpTgt) % 2 == 0 else 1))


def simplify(sName):
    dls = {'?', '!', ':', ';', '\'', '`', '\"'}
    if not sName is None:
        for ff in dls:
            sName = sName.replace(ff, "")
        return sName.lower()
    else:
        return sName


def insertRank(dbCon, dbName, musicTB, maxIdMusic, rank):
    logger.debug(
        "Inserting music rank into music Table {tb}".format(tb=musicTB))

    sql = """update {db}.{tb} set currentrank = {ra} where idMusic={idx}"""
    sql = sql.format(db=dbName, tb=musicTB, ra=rank, idx=maxIdMusic)

    return sendQuery(dbCon, sql, mode="DML")


if __name__ == "__main__":

    # setting define directory
    PHANTOMJS_PATH = "/usr/bin/phantomjs"

    # parsing argument
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--uID", required=True,
                        metavar="userID", type=str, help="user id")
    parser.add_argument("-s", "--musicsList", required=False,
                        nargs="+",  help="music file or directory having them")
    parser.add_argument("-op", "--operation", required=False,
                        choices={'add', 'rm'}, help="add or remove user account")
    parser.add_argument("-l", "--log", required=False,
                        action="store_true", help="make log file in account directory")
    # parser.add_argument("-r", "--rank", required=False, action="store_true",
    #                     help="update music rank based on melop top 100 chart")
    parser.add_argument("-up", "--update", required=False, action="store_true",
                        help="update database based on music in the directory")
    args = parser.parse_args()

    # setup logging
    logger = logging.getLogger(args.uID)
    fomatter = logging.Formatter(
        '[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')

    if (args.log):
        fileHandler = logging.handlers.RotatingFileHandler(
            HOME_DIR+args.uID+".log", maxBytes=1024*1024*10, backupCount=5)
        fileHandler.setFormatter(fomatter)
        logger.addHandler(fileHandler)

    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(fomatter)
    logger.addHandler(streamHandler)

    logger.setLevel(logging.INFO)
    # logger.setLevel(logging.DEBUG)

    logger.debug("Handling argument")

    if(args.operation == "add"):
        logger.debug("Add user ----")
        try:
            userInfo
        except NameError:
            userInfo = getUserAccount(
                "Welcome Home_Music.\n{uid}\'s account will be created".format(uid=args.uID), args.uID)
        addUser(dbCon, DB_NAME, USER_TB, HOME_DIR, userInfo)

    elif(args.operation == "rm"):
        logger.debug("remove user ----")
        try:
            userInfo
        except NameError:
            userInfo = {'uid': args.uID, 'passwd': "", 'privilege': False}

        removeUser(dbCon, DB_NAME, USER_TB, HOME_DIR, userInfo)

    if (args.rank):
        logger.debug("update rank based on melon top 100 chart")
        try:
            userInfo
        except NameError:
            userInfo = getUserAccount("Welcome Home_Music.", args.uID)

        updateRank(dbCon, DB_NAME, userInfo['uid'], PHANTOMJS_PATH)

    if (args.update):
        logger.debug("update database based on melop top 100 chart")
        try:
            userInfo
        except NameError:
            userInfo = getUserAccount("Welcom Home_Music.", args.uID)
        updateMusicDB(dbCon, DB_NAME, userInfo['uid'], [
                      os.path.join(HOME_DIR, userInfo['uid']), ])

    if(args.musicsList):
        try:
            userInfo       # check if userinfo is defined or not
        except NameError:
            userInfo = getUserAccount("Welcome Home_Music.", args.uID)

        if (existUser(dbCon, DB_NAME, USER_TB, userInfo)):
            if (checkUser(dbCon, DB_NAME, USER_TB, userInfo, """where loginID='{uid}' and passwd='{pwd}'""")):
                addMusic(dbCon, DB_NAME, HOME_DIR, userInfo, args.musicsList)
            else:
                logger.error("{uid}\'s password is incorrect".format(
                    uid=userInfo['uid']))
        else:
            logger.error("{uid} is not a user. please add user accout first".format(
                uid=userInfo['uid']))
