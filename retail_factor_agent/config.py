from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AgentConfig:
    project_root: Path = Path(__file__).resolve().parent.parent
    workspace_dir: Path = Path(__file__).resolve().parent / "workspace"
    data_dir: Path = Path(__file__).resolve().parent / "workspace" / "data"
    output_dir: Path = Path(__file__).resolve().parent / "workspace" / "outputs"
    model_dir: Path = Path(__file__).resolve().parent / "workspace" / "models"

    # Input references (reuse existing research assets without moving them)
    factor_table_path: Path = Path(__file__).resolve().parent.parent / "analysis_results" / "matched_data_2024.csv"
    existing_posts_path: Path = Path(__file__).resolve().parent.parent / "run_data" / "guba_posts_cleaned_min100.csv"
    wind_script_path: Path = Path(__file__).resolve().parent.parent / "wind_a_stock_data" / "get_wind_data.py"

    # Crawl/sample settings
    start_date: str = "2020-01-01"
    end_date: str = "2024-12-31"
    sample_size: int = 5000
    random_seed: int = 42
    min_chars: int = 100
    exclude_ai_generated: bool = True
    exclude_announcements: bool = True
    require_logic: bool = True

    # LLM settings
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_timeout: int = 60
    llm_workers: int = 8
    llm_max_input_chars: int = 1500
    llm_max_output_tokens: int = 700

    def ensure_dirs(self) -> None:
        for d in (self.workspace_dir, self.data_dir, self.output_dir, self.model_dir):
            d.mkdir(parents=True, exist_ok=True)
