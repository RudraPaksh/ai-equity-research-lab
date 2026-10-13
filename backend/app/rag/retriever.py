from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
@dataclass
class Document: id:str; title:str; text:str; source:str
class Retriever:
    def __init__(self): self.docs=[]; self.v=None; self.m=None
    def rebuild(self):
        self.v=TfidfVectorizer(stop_words="english",max_features=20000); self.m=self.v.fit_transform([d.text for d in self.docs]) if self.docs else None
    def add(self,d): self.docs.append(d); self.rebuild()
    def search(self,q,k=5):
        if not self.docs:return []
        scores=cosine_similarity(self.v.transform([q]),self.m)[0]; ids=scores.argsort()[::-1][:k]
        return [{"id":self.docs[i].id,"title":self.docs[i].title,"source":self.docs[i].source,"score":float(scores[i]),"text":self.docs[i].text} for i in ids]
