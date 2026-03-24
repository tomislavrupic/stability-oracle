from setuptools import find_packages, setup


setup(
    name="stability-oracle",
    version="0.1.0",
    description="Portable plan-stability scanner for directed workflow trajectories.",
    packages=find_packages(include=["oracle", "oracle.*", "cli", "cli.*", "haos_iip_skill", "haos_iip_skill.*"]),
    package_data={"haos_iip_skill": ["schema.json"]},
    entry_points={
        "console_scripts": [
            "stability-oracle-scan=cli.scan_plan:main",
            "haos-iip-skill=haos_iip_skill.skill:main",
        ]
    },
)
