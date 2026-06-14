"""Benchmark 测评任务输入校验 Schema"""

from marshmallow import Schema, ValidationError, fields, validate, validates


BENCHMARK_SUITES = [
    "air_bench", "beavertails", "coconot", "longsafety", "pku_saferlhf",
    "safetybench", "strongreject", "xstest", "simpleqa", "truthfulqa",
    "sycophancy_eval", "stereoset", "healthbench", "agentharm",
    "agent_threat_bench_autonomy_hijack", "agent_threat_bench_data_exfil",
    "agent_threat_bench_memory_poison", "persistbench_cross_domain",
    "persistbench_sycophancy", "cyse2_prompt_injection", "make_me_pay",
    "makemesay", "sad", "deceptionbench_aries", "wmdp_cyber", "wmdp_bio",
    "wmdp_chem", "bigcodebench", "humaneval", "mmlu", "gsm8k", "hellaswag",
    "gdm_dangerous_stealth", "uccb", "tac", "pre_flight", "medqa",
    "deceptionbench_pku", "lab_bench_dbqa", "lab_bench_litqa",
    "persistbench_beneficial_memory", "agentharm_benign", "safety_prompts",
    "sosbench", "cyse4_mitre",
]


class BenchmarkSubmitSchema(Schema):
    task_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=100),
    )
    model_name = fields.String(
        required=True,
        validate=validate.Length(min=1, max=200),
    )
    model_endpoint = fields.String(
        load_default=None,
        validate=validate.Length(max=500),
    )
    model_api_key = fields.String(
        load_default=None,
        validate=validate.Length(max=500),
    )
    benchmark_suite = fields.String(
        required=True,
        validate=validate.OneOf(BENCHMARK_SUITES),
    )
    benchmark_config = fields.Dict(load_default=None)

    @validates("task_name")
    def validate_task_name(self, value):
        if not value.strip():
            raise ValidationError("任务名称不能为空白")
