from dataclasses import dataclass, field
import json

from pathlib import Path
from typing import ClassVar

from ..scoring.scorer import ScorerInfo

from pathlib import Path 

from .dataset import Dataset 

@dataclass
class BenchmarkConfig:
    name: str
    datasets: list[Dataset]
    scorers: list[ScorerInfo]
    results_dir: Path
    pwmeval_path: Path
    metainfo: dict = field(default_factory=dict)
    
    NAME_FIELD: ClassVar[str] = 'name'
    DATASETS_FIELD: ClassVar[str] = 'datasets'
    SCORERS_FIELD: ClassVar[str] = 'scorers'
    PWMEVAL_PATH_FIELD: ClassVar[str] = "pwmeval"
    RESULTS_DIR_FIELD: ClassVar[str] = "results_dir"

    @classmethod
    def validate_benchmark_dict(cls, dt: dict):
        if not cls.NAME_FIELD in dt:
            raise Exception(
                    f"Benchmark config must has field '{cls.NAME_FIELD}'")
        if not cls.DATASETS_FIELD in dt:
            raise Exception("No information about datasets found")
        if not cls.SCORERS_FIELD in dt:
            raise Exception("No information about scorers found")

    @classmethod
    def from_dt(cls, dt: dict):
        cls.validate_benchmark_dict(dt)
        name = dt[cls.NAME_FIELD]
        datasets = [Dataset.from_dict(rec)\
                        for rec in dt[cls.DATASETS_FIELD]]
        scorers = [ScorerInfo.from_dict(rec)\
                        for rec in dt[cls.SCORERS_FIELD]]
        
        results_dir = dt.get(cls.RESULTS_DIR_FIELD)
        if results_dir is None:
            results_dir = Path("results")
        elif isinstance(results_dir, str):
            results_dir = Path(results_dir)
        results_dir = results_dir.absolute()
        
        pwmeval_path = dt.get(cls.PWMEVAL_PATH_FIELD)
        if pwmeval_path is None:
            raise Exception("PWMEval path must be provided")
        
        metainfo = dt.get('metainfo', {})

        for key, value in dt.items():
            if key not in (cls.NAME_FIELD, cls.DATASETS_FIELD, cls.SCORERS_FIELD, cls.PWMEVAL_PATH_FIELD, cls.RESULTS_DIR_FIELD):
                metainfo[key] = value

        return cls(name, 
                   datasets,
                   scorers, 
                   results_dir, 
                   pwmeval_path,
                   metainfo)

    @classmethod
    def from_json(cls, path: Path):
        with open(path, "r") as inp:
            dt = json.load(inp)
        return cls.from_dt(dt)

    #def make_benchmark(self):
    #    scorers = [cfg.make() for cfg in self.scorers]
    #    return Benchmark(self.name, 
    #                     self.datasets,
    #                     scorers,
    #                     self.results_dir,
    #                     self.metainfo, 
    #                     self.pwmeval_path)