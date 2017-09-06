# load the data
import sys
import tarfile
import os.path
import json
import re
from bz2 import BZ2File
from urllib import request
from io import BytesIO
import numpy as np
import xlrd
import nltk

# initial dictionaries for storing the feature sets
train_dict = {}
test_dict = {}
PosAff_list = []
# parse the PosAff words into a dict
workbook = xlrd.open_workbook('inquirerbasic.xls')
worksheet = workbook.sheet_by_index(0)
num_rows = worksheet.nrows
num_cells = worksheet.ncols
for r in range(num_rows):
    for c in range(num_cells):
        if r is not 0 and c is not 0: # exclude the first row and col
            if "PosAff" in worksheet.cell(r,c).value:
                # need this word
                w = worksheet.cell(r,0).value
                if '#' in w:
                    w = w.split('#')[0]
                if w in PosAff_list:
                    continue
                else:
                    PosAff_list.append(w)
# at this point we have all the PosAff words inside the PosAff list
print ("PosAff_list is : " + str(PosAff_list))


# feature extractor: uses the GIL to determine if there are any words
# that represent politeness in a given comment.
# Parameter 'comments' is a list of dict that has comments and delta info.
# GIL_data is the list of words from GIL that we are using for labelling.
# returns a list of tuples that has the form of (polite, delta) as bools.
def feature_extractor_binary(comments, GIL_data):
    # result list of dicts
    # result = []
    
    # loop through the list of dict comments:
    #for c in comments:
    for g in GIL_data:
        label_dict = {}
        if g.lower() in comments.lower():
            # this comment is labeled as "polite"
            #result.append(({'polite':'yes'}, comment_delta))
            return {'polite': 'yes'}
        #else:
            #result.append(({'polite':'no'}, comment_delta))
    #return result
    return {'polite':'no'}

# Jonathan's file
def extract_deltas(submission):
    # return a list of dicts with comment body and delta
    result_comment_list = []
    
    # first, we build a dictionary for fast lookup of comments by ID
    comment_dict = {}
    for comment in submission["comments"]:
        comment_dict[comment["name"]] = comment
    # now, we scan through the comments looking for the generic post by
    # DeltaBot marking the giving of a delta
    for i, comment in enumerate(submission["comments"]):
        sys.stdout.write("\r[DeltaExtractor] searching comment %d of %d" % (i+1, len(comment_dict)))
        # get rid of dummy comments
        if "body" not in comment:
            continue
        # when a delta is awarded, DeltaBot will comment saying "Confirmed: 1
        # delta awarded to <author>"
        if comment["author"] == "DeltaBot" and "delta awarded" in comment["body"] and comment["parent_id"] in comment_dict.keys():
            # now that we have found a delta, we must locate the comment that it
            # was awarded to. This is not nearly as straightforward as just finding
            # the grandparent comment, because in a long chain of comments the
            # author's main argument might actually be buried somewhere farther
            # up. As a heuristic, we treat the *longest* comment by the delta'd
            # author as the one that received the delta.
            parent = comment_dict[comment["parent_id"]]
            grandparent = comment_dict[parent["parent_id"]]
            author = grandparent["author"]
            # start with the assumption that the grandparent comment is the
            # delta'd comment...
            longest_comment_id = grandparent["name"]
            longest_comment_len = len(grandparent["body"])
            # ...then work our way backward up the comment chain looking for
            # other comments by the same author
            cur_comment = grandparent
            while cur_comment["parent_id"] in comment_dict:
                cur_comment = comment_dict[cur_comment["parent_id"]]
                if cur_comment["author"] == author:
                    if len(cur_comment["body"]) > longest_comment_len:
                        longest_comment_id = cur_comment["name"]
                        longest_comment_len = len(cur_comment["body"])
                        
            # here we would actually want the comment body and the delta info
            #cmnt_dict= {}
            #cmnt_dict['body'] = cur_comment["body"]
            #cmnt_dict['delta'] = 'delta'
            cmnt_dict = (comment["body"], 'delta')
            result_comment_list.append(cmnt_dict)
        else:
            # we would need the other comments to make sure we get the ones
            # that didn't receive the delta
            #cmnt_dict = {}
            #cmnt_dict['body'] = comment["body"]
            #cmnt_dict['delta'] = 'nondelta'
            cmnt_dict = (comment["body"], 'nondelta')
            result_comment_list.append(cmnt_dict)
    sys.stdout.write("Extracted all the comments...")
    return result_comment_list




fname = "cmv.tar.bz2"
url = "https://chenhaot.com/data/cmv/" + fname

# download if not exists
if not os.path.isfile(fname):
    f = BytesIO()
    with request.urlopen(url) as resp, open(fname, 'wb') as f_disk:
        data = resp.read()
        f_disk.write(data)  # save to disk too
        f.write(data)
        f.seek(0)
else:
    f = open(fname, 'rb')


tar = tarfile.open(fileobj=f, mode="r")

# Extract the file we are interested in

train_fname = "all/train_period_data.jsonlist.bz2"
test_fname = "all/heldout_period_data.jsonlist.bz2"

print("Extracting training files...")
train_bzlist = tar.extractfile(train_fname)
# Deserialize the JSON list
original_posts_train = [
    json.loads(line.decode('utf-8'))
    for line in BZ2File(train_bzlist)
]
# the list that will append all these lists from extract_deltas
train_list = []
#loop through and extract the deltas from the training set
for x in original_posts_train:
    y = json.dumps(x)
    train_list.append(extract_deltas(json.loads(y)))

print ("Extracting testing files...")
test_bzlist = tar.extractfile(test_fname)
original_posts_test = [
    json.loads(line.decode('utf-8'))
    for line in BZ2File(test_bzlist)
]
# the list that will append all these lists from extract_deltas
test_list = []
# loop through and extract the deltas from the testing set
for x in original_posts_test:
    y = json.dumps(x)
    test_list.append(extract_deltas(json.loads(y)))


# basically train_list and test_list is in the format of:
# [[(comment, delta), (comment, delta)],
# [(comment, delta), (comment, delta)]]
# where each row depicts a submission.
print ("Making the training set and the testing set...")
train_set = []
for x in train_list:
    train_set = train_set + [(feature_extractor_binary(comment, PosAff_list), delta) for (comment, delta) in x]    
#for x in train_list:
#    y = feature_extractor_binary(x, PosAff_list)
#    for t in y:
#        train_set.append(t)
print (train_set)
for x in test_list:
    test_set = [(feature_extractor_binary(comment, PosAff_list), delta) for (comment, delta) in x]    
#for y in test_list:    
#    y= feature_extractor_binary(y, PosAff_list)
#    for t in y:
#        test_set.append(t)

# train the classifier
classifier = nltk.NaiveBayesClassifier.train(train_set)
print("Classifying completed...testing on testing set")
print(nltk.classify.accuracy(classifier, test_set))

f.close()


