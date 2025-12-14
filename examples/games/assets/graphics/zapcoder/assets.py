#!python

import hashlib, re, fnmatch, os, time

def folderWalk():
    count = 0
    duplicates = 0
    rootPath = "."
    pattern = "*.png"
    f = {}
    print rootPath
    for root, dirs, files in os.walk(rootPath):
        for filename in fnmatch.filter(files, pattern):
            # remove text in brackers, make lower case, split into tags
            tags = re.sub(r'\([^)]*\)', '', root[2:]).lower().replace("/"," ").replace("  "," ").split(" ") 
            if (("hero" in tags) and (not "player" in tags)):
                tags.append("player")
            user = root[2:].split("/")[0]
            path = os.getcwd() + "/" + root[2:] + "/" + filename
            #checksum = hashlib.md5(path) #hashlib.sha384(path)
            checksum = hashlib.sha384(open(path).read()).hexdigest()
            if (checksum in f.keys()):
                print "Skipping duplicate: %s\nMatches: %s" % (path , f[checksum])
                duplicates += 1
                next
            f[str(checksum)] = path
            print "Asset:\t%s\nUser:\t%s\nTags:\t%s\nPath: \t%s\nCheck:\t%s\n" % (filename, user, tags, path, checksum)
            count += 1
    print "#Count: %s\n#Duplicates: %s" % (count, duplicates)
			
def main():
	t = time.clock()
	folderWalk()
	t = time.clock() - t 
	print "#%s seconds" % t
	
if __name__ == '__main__': 
	main()