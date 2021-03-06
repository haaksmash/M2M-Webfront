from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError

from themoviedb.tmdb import search, getMovieInfo, TmdHttpError


import re
import datetime

from search.models import File
from problems.models import DNEProblem, SavingProblem, ProblemSet, BadFileProblem
from advancedsearch.models import *

def cleanHouse():
    from django.db.models import Count
    
    
    # movie models without files
    print("Movies:")
    empties = Movie.objects.annotate(num_f=Count('files')).filter(num_f__lt=1)
    for movie in empties:
        try:
            print(u"  cleaning out #{:d} {}".format(movie.id,movie.name))
        except:
            pass

        try:
            movie.delete()
        except Exception, e:
            print(u"    Exception: {}".format(e))
    
    # music models without files
    print("Songs:")
    empties = Song.objects.annotate(num_f=Count('files')).filter(num_f__lt=1)
    for song in empties:
        try:
            print(u"    cleaning out #{:d} {}".format(song.id,song.name))
        except:
            pass

        try:
            song.delete()
        except Exception, e:
            print(u"  Exception: {}".format(e))
    print("Albums:")
    empties = Album.objects.annotate(num_s=Count('song')).filter(num_s__lt=1)
    for album in empties:
        try:
            print(u"  cleaning out #{:d} {}".format(album.id,album.name))
        except:
            pass

        try:
            album.delete()
        except Exception, e:
            print(u"    Exception: {}".format(e))
    print("Artists:")
    empties = Artist.objects.annotate(num_a=Count('album')).filter(num_a__lt=1)
    for artist in empties:
        try:
            print(u"  cleaning out #{:d} {}".format(artist.id,artist.name))
        except:
            pass

        try:
            artist.delete()
        except Exception, e:
            print(u"    Exception: {}".format(e))
        
    return


def logComplaints(issues=False):
    ''' issues should be in (problemfiles,couldnotmatchfiles) format'''
    if not issues:
        return
    # fuck the saveSet for now, it's not as interesting.
    #saveSet = File.objects.filter(id__in=[x.id for x in saveIssues])
    
    for f in issues['nomatches']:
        try:
            pset = f.path.hid.problems
        except:
            pset = ProblemSet.objects.create(host=f.path.hid)
        try:
            f.dneproblem
        except:
            prob = DNEProblem(file=f)
            prob.save()
            pset.dneproblem_set.add(prob)
            pset.save()
    
    return

    
def clean_slate(candidate):
    candidate.remove_problems()
    try:
        pset = candidate.path.hid.problems
    except Exception, e:
        try:
            pset = ProblemSet()
            pset.host = candidate.path.hid
            pset.save()
        except:
            candidate.delete()
            return None
    return pset
def crawlForMovies(count=0):
    ''' Imports things that are recognized as Movies from File table'''
    
    # grab all video files from things with Movie in the path name,
    # excluding things whose filename begin with '.' or '_'
    print "Filtering out non-({})".format(File.videoEndings)
    candidates = File.objects.filter(filenameend__regex=r'({})'.format(File.videoEndings))
    
    dirExcludes = "[pP]orn"
    print "Filtering out things in ({}) directories, things not in movies".format(dirExcludes)
    candidates = candidates.exclude(path__fullname__regex='({})'.format(dirExcludes))\
                           .filter(path__fullname__icontains='Movies')\
                           .exclude(filename__istartswith='.')\
                           .exclude(filename__istartswith='_')
    
    
    
    # We should now have all likely video files.
    # Filter according to the regexp
    # (.)*( \((([a-zA-Z]) (- )?)?[12][0-9][0-9][0-9]\)\)?.(.)*
    # Filename[ ([Director [- ]]Year)].filenameend
    # so that we can use this shit with tmdb/imdb
    print "Narrowing down filenames a little further to deal with \"(director - year)\" construction"
    candidates.filter(filename__regex=r'(.)+( \(([a-zA-Z]* (- )?)?[12][0-9][0-9][0-9]\)\))?.(.)*')
    
    #issues = {}
    
    #issues['problems'] = []
    #issues['nomatches'] = []
    
    total = len(candidates)
    print "{:d} files to check. Here we go...".format(total)
    for candidate in candidates[count:]:
        if candidate.goodfile == 0:
            print "Marked as bad file; skipping..."
            continue
        pset = clean_slate(candidate)
        if pset == None:
            continue
        count += 1
        # skip all of this if the file already has a movie
        print candidate.id
        try:
            if candidate.MIDs != None:
                print "  Candidate file %s is already recognized; moving on!" % candidate.id
                continue
        except ObjectDoesNotExist:
            # an old movie file was deleted
            print "  Previous movie no longer extant, resetting link..."
            candidate.MIDs = None
            candidate.save()
        # get rid of the file extension
        print "#%d out of %d" % (count, total)
        print "  Candidate (ID %d): %s " % (candidate.id, candidate)
        print "  slicing off extension..."
        sliceIndex = candidate.filename.rfind('.')
        info = candidate.filename[:sliceIndex]
        
        # some people (coughWOPRcough) like to use '\.' instead of spaces, in their filenames.
        # fuck those people.
        info = re.split("\.",info)
        info = u" ".join(info)
        info = re.split("\((.*)\)",info)
        
        
        # also '_'
        probablyTitle = info[0].rstrip().replace('_',' ').replace('-',' ')
        
        # ignore anything between {}
        
        probablyTitle = re.sub(r'{.*}','',probablyTitle)
        probablyTitle = probablyTitle.replace('  ',' ')
        
        # now, clean up MORE BULLSHIT;
        # screw you guys, we know it's 1080 or 720 or BLURAY
        # because it's a fucking HUGE file. Seriously.
 #       probablyTitle = probablyTitle.replace(' 1080p','').replace(' 720p','').replace(' bluray','')\
 #                       .replace(' hdtv','').replace(' 456p','').replace(' dvd','').replace(' 524p','')\
 #                       .replace(' 368p','').replace(' 400p','').replace(' 480p','').replace(' 336p','')\
 #                       .replace(' 432p','').replace(' tv','').replace(' 340p','').replace(' 346p','')\
 #                       .replace(' 455p','')
        # oh my god fuck this
        
        print "    Stripping out retarded information..."
        extraShit = ['[',']',' dvdrip',' dvdscr',' hddvd',' dvd',' hdtv',' tv',' bluray',' ts',]
        for shit in extraShit:
            probablyTitle = probablyTitle.replace('%s'%shit,'')
            
        # fuck youu ###(#)?pppppp
        bitches = re.split(" \d{3,4}p",probablyTitle)
        
        probablyTitle = ''.join(bitches)
        # get some meta-data
        print "  Stripping metadata out of title, if it's there."
        if len(info) > 1:
            meta = re.search('((?P<DIRECTOR>(.+)) - )?(?P<YEAR>\d{4})', info[1])
            try: # if there's a year
                try:
                    year = meta.group('YEAR')
                    print "  Found year data."
                except:
                    print "  No year data."
                    year = ""
            except KeyError:
                year = ""
        else:
            year = ""
                
        # find movies that match the title
        string = "  Querying TMDB... (%s) " % probablyTitle
        print string.encode('utf-8')
        try:
            movies = search("%s %s" % (probablyTitle, year))
        except TmdHttpError, e:
                print "  TMDB not available: \n\t%s" % e
                return
                
        if len(movies) > 0:
            print "  Found something!"
            candidate.remove_dne_problem()
        else:
            # add problem for later perusal
            candidate.remove_dne_problem()
            prob = DNEProblem()
            prob.file = candidate
            prob.save()
            pset.dneproblem_set.add(prob)
            pset.save()
            
            print "  No love. Moving on!"
            #issues['nomatches'] += [candidate]
            continue
            
        # only take the first result, which is the most likely
        
        for movieresult in movies[:1]:
            # now, get the info and put in the DB - if it's not already there.
            try:
                checker = Movie.objects.get(pk=int(movieresult['id']))
                print "    Movie already in database; no new entry made."
                print "    Checking to see if this is a new file..."
                if candidate in checker.files.all():
                    print "    Not a new file, moving on."
                    continue
                else:
                    print "    New file! adding to list of sources..."
                    checker.files.add(candidate)
                    checker.save()
            # this exception means, obviously, it's a new movie:
            except ObjectDoesNotExist:
                movie = getMovieInfo(movieresult['id'])
                
                print "    Movie not in database: %s\n" % movie['name'].encode('utf-8')
                certification=movie['certification'],
                latestEntry = Movie(
                            id=int(movieresult['id']), # for API compatibility
                            rating=movie['rating'],
                            votes=int(movie['votes']),
                            name=movie['name'].encode('utf-8'),
                            dateadded=datetime.datetime.now(),
                            url=movie['url'],
                            overview=movie['overview'] if movie['overview'] else 'No overview available',
                            popularity=int(float(movie['popularity'])),
                            imdb_id=movie['imdb_id'] if movie['imdb_id'] else None, # in case we ever want to use imdb data
                            released=movie['released'] if movie['released'] else None,
                            adult=True if movie['adult']=='true' else False,
                            director=movie['cast']['director'][0]['name'] if movie['cast'].has_key('director') else 'Unknown',
                            runtime=str(datetime.timedelta(minutes=int(movie['runtime']))) if movie['runtime'] else None,
                            )
                            
                # setting images for the movie - ugly try/escape chain, sorry
                try:
                    latestEntry.backdrop=movieresult['images'][1]['poster'] if len(movie['images'])>1 and movie['images'][1].has_key('poster') else '/media/images/no_backdrop.jpg'
                except IndexError:
                    latestEntry.backdrop= '/media/images/no_backdrop.jpg'
                try:
                    latestEntry.poster = movie['images'][0]['cover'] if len(movie['images'])>0 and movie['images'][0].has_key('cover') else '/imaging/no_poster/{}'.format(movie.id)
                except:
                    latestEntry.poster = '/media/images/no_poster.jpg'
                try:
                    latestEntry.thumb = movie['images'][0]['thumb'] if len(movie['images'])>0 and movie['images'][0].has_key('thumb') else '/media/images/no_thumb.jpg'
                except:
                    latestEntry.thumb = '/media/images/no_thumb.jpg'            
                            
                print "    adding %s to movie's file set..." % candidate
                latestEntry.files.add(candidate)
                # we have to save here, or the loop below will fail due to no entry in
                # the movies table
                try:
                    latestEntry.save()
                except:
                    print "    Something went wrong; moving on."
                    prob = SavingProblem()
                    prob.file = candidate
                    prob.save()
                    pset.savingproblem_set.add(prob)
                    pset.save()
                    #issues['problems']+= [candidate]
                    
                candidate.remove_saving_problem()
                
                
                print "    setting %s to movie's certification..." % movie['certification']
                if len(MovieCert.objects.filter(cert="None" if movie['certification']==None else movie['certification'])) == 0:
                    print  "      Found a new cert, adding to database..."
                    cert = MovieCert.objects.create(cert="None" if movie['certification']==None else movie['certification'])
                else:
                    cert = MovieCert.objects.get(cert="None" if movie['certification']==None else movie['certification'])
                latestEntry.cert = cert
                
                print "    adding genres to movie's genres..."
                if movie['categories'].has_key('genre'):
                    for genre in movie['categories']['genre']:                    
                        if len(MovieGenre.objects.filter(name=genre)) == 0:
                            print "      Found a new genre, adding it to database..."
                            newGenre = MovieGenre(name=genre)
                            newGenre.save()
                        else:
                            newGenre = MovieGenre.objects.get(name=genre)
                        # add movie to genre and vice versa, then save genre (because we leave
                        # the genre object first!)
                        latestEntry.genres.add(newGenre)
                        newGenre.movies.add(latestEntry)
                        newGenre.save()
                else:
                    latestEntry.genres.add(MovieGenre.objects.get(name="None"))
                latestEntry.save()
               
    print "Success."
    # store problems in database
    #logComplaints(issues)
    return 
    
def crawlForMusic(count=0):
    '''
    # last.fm stuff; it's faster to use iTunes searching, for crawling.
    # maybe last.fm can be included to pages? for streaming - i like this idea
    import pylast
    password_hash = pylast.md5(password)
    network = pylast.LastFMNetwork(api_key=API_KEY,api_secret=API_SECRET,
                                   username=username, password_hash=password_hash)
    '''
    # iTunes api stuff
    import json, urllib
    searchbase = "http://ax.phobos.apple.com.edgesuite.net/WebObjects/MZStoreServices.woa/wa/wsSearch"
    lookupbase = "http://ax.phobos.apple.com.edgesuite.net/WebObjects/MZStoreServices.woa/wa/wsLookup"
    
    print "Filtering out non-({})".format(File.audioEndings)
    candidates = File.objects.filter(filenameend__regex=r'({})'.format(File.audioEndings))
    
    dirExcludes = None
    print "filtering out things in ({}), things not in music, and (\.|_|!)-beginning files".format(dirExcludes)
    candidates = candidates.filter(path__fullname__icontains="Music")\
                            .exclude(filename__istartswith='.')\
                            .exclude(filename__istartswith='_')\
                            .exclude(filename__istartswith='!')
    total = candidates.count() - count
    print "{:d} files to check. Here we go...".format(total)
    for candidate in candidates[count:]:
        try:
            if candidate.goodfile == 0:
                print "File marked as bad, skipping."
                continue
            pset = clean_slate(candidate)
            
            count += 1
            # skip all of this if the file already has a movie
            print candidate.id
            try:
                if candidate.MuIDs != None:
                    print "  Candidate file {} is already recognized; moving on!".format(candidate.id)
                    continue
            except ObjectDoesNotExist:
                # an old movie file was deleted
                print "  Previous song no longer extant, resetting link..."
                candidate.MuIDs = None
                candidate.save()
            # get rid of the file extension
            print "#{} out of {}".format(count, total)
            print "  Candidate (ID {}): {} ".format(candidate.id, candidate)
            print "  slicing off extension..."
            sliceIndex = candidate.filename.rfind('.')
            info = candidate.filename[:sliceIndex]
            
            print "  slicing off tracknumber, if it's there..."
            if re.match("^\d+( )?(-)?( )?",info):
                info = re.sub(r"^\d+( )?(-?)( )?",'',info)
            
            # some people (coughWOPRcough) like to use '\.' instead of spaces, in their filenames.
            # fuck those people.
            info = re.split("\.",info)
            info = u" ".join(info)
            info = re.split("\((.*)\)",info)
            
            
            # also '_'
            probablyTitle = info[0].rstrip().replace('_',' ')
    
            # ignore anything between {}
            print "  cutting out things in \{\}..."
            probablyTitle = re.sub(r'{.*}','',probablyTitle)
            probablyTitle = probablyTitle.replace('_',' ')
            probablyTitle = probablyTitle.replace('  ',' ')
            titlecopy = probablyTitle
            params = {}
            
            # hopefully nobody was retarded about this:
            probablyAlbum = unicode(candidate.path.shortname.replace('.',' ').replace('_',' ').replace('  ',' '))
            probablyArtist = unicode(candidate.path.parent.shortname.replace('.',' ').replace('_',' ').replace('  ',' '))
            try:
                # cut out artists from file name? i.e. "Oxford Comma - Vampire Weekend" -> "Oxford Comma"
                print "  cutting out probable artist name from title, if applicable"
                probablyTitle = re.sub(u'{}'.format(probablyArtist.replace(u'(',r'\(').replace(u')',r'\)')),u'',probablyTitle)
                probablyTitle = probablyTitle.replace(u' - ',u'').replace(u'  ',u' ')
            except:
                continue
            try:
                print u"Searching for {}, by {} in album: {}".format(probablyTitle,probablyArtist,probablyAlbum)
            except:
                print u"Can't print search term, OH WELL"
            params.update({'term':probablyTitle,
                           'entity':'musicTrack',
                           'attribute':'allTrackTerm',})
            try:
                url = u"{}?{}".format(searchbase,urllib.urlencode(params))
            except:
                continue
                
            try:
                resultDump = json.load(urllib.urlopen(url))
            except:
                resultDump = {'resultCount':0}
        
            if resultDump['resultCount'] == 0 and titlecopy != "":
                # wrap this in a try...except because FUCK YOU
                try:
                    print "  This is a WOPR file, that rat bastard. Making changes."
                    # Album - # - Artist - Song.mp3
                    probablyTitle = titlecopy
                    print "  Cutting out artist name from title."
                    probablyTitle = unicode(re.sub(u'{}'.format(probablyArtist.replace('(',r'\(').replace(')',r'\)')),'',probablyTitle))
                    info = re.split(' - ',probablyTitle)
                    probablyTitle = info[-1]
                    probablyAlbum = info[1]
                    params = {}
                    try:
                        print u"Searching for {}, by {} in album: {}".format(probablyTitle,probablyArtist,probablyAlbum)
                    except:
                        print u"Can't print search term, OH WELL"
                    params.update({'term':probablyTitle,
                                   'entity':'musicTrack',
                                   'attribute':'allTrackTerm',})
                    url = u"{}?{}".format(searchbase,urllib.urlencode(params))
    
                    resultDump = json.load(urllib.urlopen(url))
                except:
                    pass
            if resultDump['resultCount'] == 0:
                candidate.remove_dne_problem()
                #prob = DNEProblem()
                #prob.file = candidate
                #prob.save()
                #pset.dneproblem_set.add(prob)
                #pset.save()
                print "No love. Moving on!"
                continue
            
            results = resultDump['results']
            for result in results:
                try:
                    try:
                        print u"Result: {}:{} by {}".format(result['collectionName'],result['trackName'],result['artistName'])
                    except UnicodeEncodeError:
                        print u"Can't print some part of the result. OH WELL"
                    except Exception, e:
                        print u'whoopsie! {}'.format(e)
                        
                    if unicode(result['artistName']).lower() == probablyArtist.lower() \
                        and (unicode(result['collectionName']).lower() == probablyAlbum.lower() or \
                            unicode(result['collectionCensoredName']).lower() == probablyAlbum.lower()) \
                        and (unicode(result['trackName'].lower()) == probablyTitle.lower() or \
                            unicode(result['trackCensoredName']).lower() == probablyTitle.lower()):
                        # an exact match! yessss
                        try:
                            artist,new = Artist.objects.get_or_create(name=probablyArtist,
                                                                  appleID=result['artistId'])
                        except:
                            continue
                            
                        if new:
                            print u"New artist added to database: {}".format(artist)
                            artist.dateadded = datetime.datetime.now()
                            artist.save()
                        else:
                            print u"Already have artist: {}".format(artist)
                            
                        try:
                            album,new = Album.objects.get_or_create(name=probablyAlbum,
                                                                appleID=result['collectionId'])
                        except:
                            # some appleID shit got fucked
                            continue
                            
                        if new:
                            print u"New album added to database: {}".format(album)
                            album.appleCover = result['artworkUrl100']
                            album.explicit = True if result['collectionExplicitness'] != 'notExplicit' else False
                            album.releaseDate = datetime.datetime.strptime(result['releaseDate'], "%Y-%m-%dT%I:%M:%SZ")
                            album.dateadded = datetime.datetime.now()
                            album.no_cover = u"/imaging/music/album/no_cover/{}".format(album.id)
                            album.save()
                            print u"Adding {} to {}'s album set...".format(album,artist)
                            artist.album_set.add(album)
                        
                        
                        genre, new = MusicGenre.objects.get_or_create(name=result['primaryGenreName'])
                        if new:
                            print u"Found new genre: {}".format(genre)
                        else:
                            print u"Not a new genre: {}".format(genre)
                        
                        duration = datetime.timedelta(0,0,0,result['trackTimeMillis'])
                        print u"Duration: {}".format(duration)
                        try:
                            track,new = Song.objects.get_or_create(name=probablyTitle,artist=artist,album=album,
                                                               appleID=result['trackId'],
                                                               tracknum=result['trackNumber'],
                                                               applePreview=result['previewUrl'],
                                                               time = str(datetime.timedelta(milliseconds=result['trackTimeMillis'])),
                                                               matchtype = 1)
                        except IntegrityError: # this is BULLSHIT
                            track = Song.objects.get(appleID=result['trackId'])
                            new = False
                        if new:
                            print u"New Song - {}".format(track)
                            track.dateadded = datetime.datetime.now()
                            track.save()
                            print u"Adding to {}'s song set...".format(album)
                            album.song_set.add(track)
                            print u"Adding to {}'s song_set...".format(artist)
                            artist.song_set.add(track)
                            print u"Adding song to genre {}'s song_set...".format(genre)
                            genre.songs.add(track)
                            genre.save()
                        else:
                            print "Not a new song."
                        print u"Adding File {} to track's file set...".format(candidate.filename)
                        track.files.add(candidate)
                        # since this is a perfect match, we don't need to look through any other results
                        break
                except Exception, e:
                    print e
                    continue
                
        except Exception, e:
            print e
            continue
            
                
