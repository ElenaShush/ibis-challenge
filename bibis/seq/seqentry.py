
from __future__ import annotations
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqIO import SeqRecord
from dataclasses import dataclass
from typing import ClassVar, Iterable
from pathlib import Path
import io

from ..scoring.label import NO_LABEL, Label, str2label

NO_TAG = "__NO_TAG__"

from .utils import gc 

@dataclass
class SeqEntry:
    sequence: Seq
    tag: str = NO_TAG
    label: Label = NO_LABEL
    metainfo: dict | None = None

    LABEL_NAME: ClassVar[str] = "label"
    INFO_SEPARATOR: ClassVar[str] = ";"
    KV_SEPARATOR: ClassVar[str] = "="
    
    def __len__(self) -> int:
        return len(self.sequence)

    #TODO: is this method required? 
    def get(self, key, default=None):
        try:
            val = getattr(self, key)
            if key == "sequence":
                val = val.seq
            elif key == "label":
                val = val.name 
        except AttributeError:
            if self.metainfo is not None:
                val = self.metainfo.get(key, default)
            else:
                val = default
        return val
    
    def to_seqrecord(self) -> SeqRecord:
        if self.label != NO_LABEL:
            description = [f"{self.LABEL_NAME}{self.KV_SEPARATOR}{self.label}"]
        else:
            description = []

        if self.metainfo is not None:
            for key, value in self.metainfo.items():
                field = f"{key}{self.KV_SEPARATOR}{value}"
                description.append(field)
        description = self.INFO_SEPARATOR.join(description)
        
        record = SeqRecord(seq=self.sequence, 
                           id=self.tag,
                           name=self.tag,
                           description=description)
        return record 
    
    @classmethod
    def from_seqrecord(cls, rec: SeqRecord) -> 'SeqEntry':
        info = {}
        point = rec.description.find(" ")
        if point != -1:
            description = rec.description[point+1:]
            for field in description.split(cls.INFO_SEPARATOR):
                key, value = field.split(cls.KV_SEPARATOR)
                info[key] = value
        label = info.pop("label", None)
        if label is None:
            label = NO_LABEL
        else:
            label = str2label(label)
        return cls(sequence=rec.seq, 
                   tag=rec.name, 
                   label=label, 
                   metainfo=info)
        
    @property
    def gc(self) -> float:
        return gc(self.sequence)
               

def read_fasta(handle: io.TextIOWrapper | Path | str) -> list[SeqEntry]:
    entries = [SeqEntry.from_seqrecord(rec) for rec in SeqIO.parse(handle, format="fasta")]
    return entries

def read(handle: io.TextIOWrapper | Path | str, format: str="fasta") -> list[SeqEntry]:
    match format:
        case "fasta": 
            return read_fasta(handle)
        case _:
            raise NotImplementedError(f"No method to read {format}")

def write_fasta(entries: Iterable[SeqEntry], handle: io.TextIOWrapper | Path | str):
    records = (e.to_seqrecord() for e in entries)
    return SeqIO.write(records, handle, format="fasta-2line")

def write(entries: Iterable[SeqEntry], handle: io.TextIOWrapper | Path | str, format: str="fasta"):
    match format:
        case "fasta":
            return write_fasta(entries, handle)
        case _:
            raise NotImplementedError(f"No method to write to {format}")
        
def drop_duplicates(entries: list[SeqEntry]) -> list[SeqEntry]:
    """
    remove duplicates (sequences)
    """
    mapping: dict[Seq, SeqEntry] = {}
    for en in entries:
        mapping[en.sequence] = en
    return list(mapping.values())