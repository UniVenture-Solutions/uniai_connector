"""Customer name matching that respects words and normalizes initials."""
import re
import unicodedata


def normalize(value):
    value=unicodedata.normalize('NFKC',value).casefold()
    value=re.sub(r'[.\u2019\u0027]', '', value)
    words=re.findall(r'[^\W_]+',value,flags=re.UNICODE)
    result=[];initials=[]
    for word in words+['']:
        if len(word)==1 and word.isalpha():
            initials.append(word)
            continue
        if initials:result.append(''.join(initials));initials=[]
        if word:result.append(word)
    return ' '.join(result)


def rank_customers(query, rows):
    q=normalize(query)
    if not q:return []
    tokens=q.split();matches=[]
    for row in rows:
        score=0
        for value in (row['name'],row['customer_name']):
            text=normalize(value);words=text.split()
            if text==q:rank=4
            elif text.startswith(q+' '):rank=3
            elif all(t in words for t in tokens):rank=2
            elif all(t in words or (len(t)>=3 and any(w.startswith(t) for w in words)) for t in tokens):rank=1
            else:rank=0
            score=max(score,rank)
        if score:matches.append((score,row))
    return [r for _,r in sorted(matches,key=lambda x:(-x[0],x[1]['customer_name'].casefold(),x[1]['name']))]
