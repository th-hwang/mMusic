import mutagen
from mutagen.id3 import ID3
import sys


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


def simplify(sName):
    dls = {'?', '!', ':', ';', '\'', '`', '\"'}
    if not sName is None:
        for ff in dls:
            sName = sName.replace(ff, "")
        return sName.lower()
    else:
        return sName


if __name__ == "__main__":

    # tag = mutagen.File("002.mp3")
    tag = ID3("002.mp3")

    print(tag['TIT2'].encoding)
    # kk = str(tag['TIT2'].text[0], encoding=tag['TIT2'].encoding)
    # print(tag.tags)

    # print(tag['TPE1'].text[0].replace(' ', '_'))

    # for key, value in tag.items():
    #     if not "APIC" in key and not "USLT" in key:
    #         print(key, end="")
    #         print(" : ", end="")
    #         print(simplify(value.text[0]))
