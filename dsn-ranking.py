import re
import os
import traceback

import dblp
import json
import time
import datetime
import pickle

## Constants
OUTPUT_DIR = './output'               # Output directory
MIN_PAGES = 4                         # Min pages for a paper
MATCH = ['DSN', 'FTCS']               # Venues considered
# DOI considered (to filter out workshops)
MATCH_DOI = [
    '10\.1109/DSN([0-9]+)\.{}\.([0-9]+)',
    '10\.1109/ICDSN\.{}\.([0-9]+)',
    '10\.1109/DSN\.{}\.([0-9]+)',
    '10\.1109\/FTCS\.{}\.([0-9]+)']
RECENT_YEARS = 5                       # Number years span used to consider a publication as 'recent'
WAIT_TIME = 5                          # Wait time in seconds. We are throttling the connections with dblp to avoid being soft ban

## Global Variables
authorList = {}


def get_recent_pubs(pubs):
    """Get the number of recent publications (using the `RECENT` constant as reference.
    Args:
        pubs: List of publications for the author.

    Returns:
        The number of publications that qualify as recent.
    """
    cc = 0
    for key in pubs:
        # in case the year has a suffix (e.g., LeeL17a)
        try:
            yyy = int(key[len(key) - 2:])
        except:
            yyy = int(key[len(key) - 3:len(key) - 1])
        yyy = yyy + 1900 if yyy > 50 else yyy + 2000
        if yyy >= RECENT:
            cc += 1
    return cc

def update_authors(pid, name, key):
    """Update the author list (`authorList`)
    Args:
        pid: Identifier of the author.
        name: Name of the author
        key: Key of the publication

    Returns:
        None
    """
    if pid in authorList:
        author = authorList[pid]
        author["pubs"].add(key)
        authorList[pid] = author
    else:
        author = {
            'name': name,
            'pubs': {key}
        }
        authorList[pid] = author


def filter_papers(pub, venue):
    """Filter out papers from the count (e.g., Industrial Track, Workshop papers, etc)
    Returns:
        True if the paper should be considered. False otherwise.
    """
    year = int(venue[len(venue)-4:])
    pags = 0

    # Check number of pages. Discard keynotes or abstract
    if 'pages' in pub:
        if '-' not in pub['pages']:
            pags = 1
        else:
            try:
                pages = pub['pages'].split('-')
                pags = int(pages[1]) - int(pages[0]) + 1
            except:
                # For some papers, pages does not include the finish page of the publication.
                pags = 99
    if pags < MIN_PAGES:
        return False

    # Filter out workshops, industry track, supplemental volume, etc
    if pub["venue"] in MATCH:
        # Papers from main conference can be distinguished by the doi. For example, a paper from a workshop has a doi
        # with DSN-W.YYYY, while the papers from the main conference has a doi with DSN.YYYY.
        # For some papers the doi is not available (e.g., https://dblp.uni-trier.de/rec/xml/conf/ftcs/HuangK93.xml)
        for doi in MATCH_DOI:
            try:
                regex = r"%s" % doi.format(year)
                match = re.search(regex, pub["doi"])
                # print ("%s %s" % (regex, pub["doi"]))
                if match != None:
                # if doi.format(year) in pub["doi"]:
                    return True
            except KeyError as e:
                # if the paper does not have a doi
                print(f"DOI not found for {pub}")
                return True
            except Exception as e:
                print(f"DOI:{pub['doi']} does not match for {pub}")
                return True

    return False

def get_authors(venue):
    """Save the author list (in `authorList`) who had accepted papers in the conference.
    Args:
        venue: venue to search. The venue follows this format /conf/XXX/YYYY, where XXX is the abbrev of the conf and
        YYYY correspond to the year of the conf.

    Returns:
        The number of publications (main conference) for the venue
    """
    papers=0
    results = dblp.search_pub(venue)

    try:
        hits = json.loads(results)["result"]["hits"]

        # No hits for the `conf/dsn/{}".format(year)`
        # Most probably either the venue prefix is wrong or there are no paper selected for the current year
        if "hit" not in hits:
            return 0

        for i in hits["hit"]:
            info = i["info"]
            if  filter_papers(info, venue):
                papers+=1
                # print(info)
                if 'authors' in info:
                    if isinstance(info["authors"]["author"], list):
                        # Multiple collaborators
                        for author in info["authors"]["author"]:
                            update_authors(author["@pid"], author["text"], info["key"])
                    else:
                        # Solo author
                        author = info["authors"]["author"]
                        update_authors(author["@pid"], author["text"], info["key"])

        return papers

    except:
        traceback.print_exc()
        return 0

def usage():
    """Print out script usage.
    """
    if not os.path.isdir(OUTPUT_DIR):
        if OUTPUT_DIR[0:2] == './':
            dir = OUTPUT_DIR[2:]
        else:
            dir = OUTPUT_DIR
        os.makedirs(dir)

    return True

def persist_authors(authors: dict, filename: str):
    """Persists authorList as a JSON file.
    Args:
        authors: dict with the list of authors
        filename: filename of the JSON file

    Returns:

    """

    # Prepare dict for serialization
    serializable_dict = {}

    for key, value in authors.items():
        value['pubs'] = list(value['pubs'])
        value['pid'] = key
        serializable_dict[key] = value

    # Dump data to JSON file
    try:
        with open(filename, 'w') as f:
            json.dump(serializable_dict, f, indent=4)
        print(f"Author list was successfully save to {filename}")
    except TypeError as e:
        print(f"Error trying to save author list: {e}")

def main():
    """Main Function
    Returns:
        None
    """

    if not usage():
        exit(1)

    # Getting the year used to determine 'recent' publications
    cyear = datetime.datetime.now().year
    cyear = int(cyear) + 1
    global RECENT
    RECENT = cyear - RECENT_YEARS

    print ('Last: {} | Recent papers since: {}'.format(cyear-1, RECENT))

    outFile = open(OUTPUT_DIR + '/dsnHOF-' + time.strftime("%Y%m%d-%H%M%S"), mode='a', encoding='utf-8')

    # FTCS (1988-1999)
    print ('Processing FTCS (1988, 1999)')
    for year in range(1988,2000):
        time.sleep(WAIT_TIME)
        print(" * Processing year {}: {}".format(year, get_authors("conf/ftcs/{}".format(year))))

    # DSN (2000-now)
    print ('Processing DSN (2000, %d)' % (cyear-1))
    for year in range(2000,cyear):
        time.sleep(WAIT_TIME)
        print(" * Processing year {}: {}".format(year, get_authors("conf/dsn/{}".format(year))))

    # Checkpoint
    persist_authors(authorList, "authorlist.json")

    for pid in authorList:
        author = authorList[pid]
        author['total'] = len (author["pubs"])
        author['recent'] = get_recent_pubs(author["pubs"])
        authorList[pid] = author

        outFile.write("{}\t{}\t{}\t{}\n".format(author["name"], author["total"], author["recent"], author["pubs"]))

    outFile.flush()

    # Getting author's data
    # Sort by total publications
    rank=1
    last_total=0
    i=1
    data = []
    for key, value in sorted(authorList.items(), key=lambda x : x[1]['total'], reverse=True):

        if i > 90000 and last_total != value['total']:
            break

        if rank > 200:
            break

        if last_total != value['total']: rank = i

        try:
            affiliation = dblp.get_affiliation(key, value['name'])
            time.sleep(WAIT_TIME)
        except:
            affiliation = "Unknown"
            print ('{} {}: affiliation not found.'.format(key, value['name']))
            traceback.print_exc()

        print(f"""{rank}\t{key}\t{value['name']}\t{value['total']}\t{value['recent']}\t{affiliation}""")
        # print ('{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(i, rank, key, value['name'], value['total'], value['recent'], affiliation))
        data.append({
            "anchor": "ranking",
            "num": i,
            "rank": rank,
            "author": value['name'],
            'total': value['total'],
            'recent': value['recent'],
            'affiliation': affiliation
        })

        i+=1
        last_total = value['total']

    print("Saving ranking.json...")
    with open('./ranking.json', mode='w', encoding='utf-8') as jsonFile:
        json.dump(data, jsonFile, indent=4)


def test():
    xx = [
        {'ikey': "i/RavishankarKIyer", 'name': "Ravishankar K. Iyer"},
        {'ikey': "33/2879", 'name': "Henrique Madeira"}
    ]
    # xx = dblp.get_affiliation("i/RavishankarKIyer", "Ravishankar K. Iyer")
    # xx = dblp.get_affiliation("k/PhilipKoopman", "Philip J. Koopman Jr.")
    # xx = dblp.get_affiliation("50/842","Daniel P. Siewiorek")
    # xx = dblp.get_affiliation("l/MichaelRLyu", "Michael R. Lyu")
    # xx = dblp.get_affiliation("k/JoostPieterKatoen", "Joost-Pieter Katoen")
    # xx = dblp.get_affiliation("33/2879", "Henrique Madeira")
    
    for entry in xx:
        print(entry)
        print(f"{entry['ikey']}, {entry['name']}: {dblp.get_affiliation(entry['ikey'], entry['name'])}")

if __name__ == '__main__':
    main()
    # test()
    print("Done!")