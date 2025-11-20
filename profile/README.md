# Single-Molecule Sequencing (SMS) Lab

**Error-Aware Pharmacogenomics through Probabilistic Pipeline Design**

---

## 🧬 The SMS Pipeline: P(h,g,u,d,ℓ,σ,r,C,A)

At the heart of our research is a **Markov-structured probabilistic pipeline** that transforms biological hypotheses into actionable clinical insights with quantified uncertainty:

```
P(h,g,u,d,ℓ,σ,r,C,A) = P(h) · P(g|h) · P(u|g) · P(d|u) · P(ℓ|d) · P(σ|ℓ) · P(r|σ) · P(C|r) · P(A|r)
```

### Pipeline Stages

| Stage | Symbol | Name | Purpose |
|-------|--------|------|---------|
| **h** | 𝒽 | **Haplotype** | Define target genetic variants and diplotypes |
| **g** | 𝑔 | **Construct** | Design plasmid standards via Golden Gate assembly |
| **u** | 𝓊 | **Enrichment** | CRISPR/Cas9 adaptive sampling for target genes |
| **d** | 𝒹 | **Fragment** | Prepare DNA libraries for sequencing |
| **ℓ** | ℓ | **Library** | Load samples onto nanopore flow cells |
| **σ** | 𝜎 | **Signal** | Raw ionic current measurements |
| **r** | 𝓇 | **Read** | Basecalling with Dorado (HAC/SUP models) |
| **C** | 𝒞 | **Cas9** | Toggle for enrichment-based workflows |
| **A** | 𝒜 | **Adaptive** | Real-time selective sequencing |

### Key Innovation: SMA-seq (Single Molecule Accuracy Sequencing)

**Bayesian error calibration** using plasmid-based DNA standards to achieve clinical-grade pharmacogenomic sequencing with quantified uncertainty.

---

## 🔬 Research Focus

### Primary Research Areas

1. **Pharmacogenomics** (PGx Team)
   - CYP2D6, CYP2B6, and other drug-metabolizing enzymes
   - Singapore breast cancer cohort: 50+ patients
   - Clinical guidelines via CPIC integration

2. **Golden Gate Assembly** (Golden Gate Cloning Team)
   - 72-fragment hierarchical cloning system
   - 11.3kb CYP2D6 assembly with 96% silent mutation rate
   - Plasmid standards for error calibration

3. **Adaptive Sampling** (ONT Adaptive Team)
   - Real-time target enrichment
   - Cost-effective pharmacogene sequencing ($350/patient)
   - CRISPR/Cas9 integration (Cas9 Enrichment Team)

4. **AI Basecalling** (AI Basecaller Team)
   - Dorado model optimization for SMS pipeline
   - Custom training for pharmacogene accuracy
   - Signal processing innovations (σ stage)

5. **Mathematical Framework** (Core Math Team)
   - Bayesian error models
   - Perfect read probability analysis
   - YAML-based mathematical registry

6. **Bioinformatics** (Bioinformatics Team)
   - SEER pipeline: Single-molecule Error Estimation for Reads
   - wf-pgx workflow for pharmacogenomics
   - HPC optimization (Great Lakes, HTC Team)

---

## 📚 Repositories

### Core Infrastructure

- **[SMS_infrastructure](https://github.com/Single-Molecule-Sequencing/SMS_infrastructure)** - Schemas, validation, templates, and automation
- **[sms-core-math](https://github.com/Single-Molecule-Sequencing/sms-core-math)** - Mathematical knowledge registry (YAML-based)
- **[sms-pipeline](https://github.com/Single-Molecule-Sequencing/sms-pipeline)** - Computational pipeline documentation

### Active Manuscripts

- **[paper-end-reason](https://github.com/Single-Molecule-Sequencing/paper-end-reason)** - Nanopore sequencing run quality analysis
- **[paper-singapore-cohort](https://github.com/Single-Molecule-Sequencing/paper-singapore-cohort)** - Breast cancer pharmacogenomics study

### Educational Resources

- **[SMS_textbook](https://github.com/Single-Molecule-Sequencing/SMS_Textbook)** - SMS Haplotype Framework textbook

---

## 🧪 Laboratory Capabilities

### Wet Lab (BSL1, BSL2, UM-PHI, UM-NCCS)
- Golden Gate cloning (Type IIS restriction enzymes: BsaI, BsmBI)
- Sanger sequencing validation (1000+ reactions)
- Oxford Nanopore sequencing (MinION, PromethION)
- Flow cell washing and reuse protocols
- CRISPR/Cas9 gRNA design

### Dry Lab
- Great Lakes HPC (University of Michigan)
- Dorado basecalling (HAC, SUP models)
- PharmCAT pharmacogenomics pipeline
- wf-pgx targeted long-read analysis
- Interactive mathematical tools (100+ calculators)

---

## 🎯 Clinical Impact

### Key Findings

- **42%** of breast cancer patients had CYP2D6 structural variants requiring long-read sequencing
- **$350/patient** cost (vs $800-1200 traditional methods)
- **Clinical-grade** accuracy via Bayesian error calibration
- **Quantified uncertainty** for all variant calls

### Collaborations

- **National Cancer Centre Singapore (NCCS)** - Clinical validation cohort
- **Rogel Cancer Center (University of Michigan)** - Research partnership
- **Phenomics Health Inc.** - Industry collaboration
- **UM Phenomics Health Institute (UM-PHI)** - Proficiency testing

---

## 📊 Project Organization

### Team Structure (10 Teams)

Our work is organized by pipeline stage and domain expertise:

1. **Golden Gate Cloning Team** (g stage)
2. **Cas9 Enrichment Team** (C toggle)
3. **ONT Adaptive Team** (A toggle)
4. **SMA-seq Team** (end-to-end methodology)
5. **AI Basecaller Team** (r stage)
6. **Bioinformatics Team** (σ, r stages)
7. **PGx Team** (h stage, clinical applications)
8. **Core Math Team** (probabilistic framework)
9. **Data Management Team** (infrastructure)
10. **HTC Team** (high-throughput computing)

### Pipeline Stage Labels

All issues and pull requests are tagged by pipeline stage:
- `Stage: h (Haplotype)` - Target variant definition
- `Stage: g (Construct)` - Plasmid design
- `Stage: u (Guide/Capture)` - Enrichment design
- `Stage: d (Fragment)` - Library preparation
- `Stage: ℓ (Library)` - Sequencing setup
- `Stage: σ (Signal)` - Raw data processing
- `Stage: r (Read/Basecall)` - Base calling
- `Stage: C (Cas9 toggle)` - CRISPR experiments
- `Stage: A (Adaptive toggle)` - Real-time sequencing

---

## 🚀 Getting Started

### For Collaborators

1. Review the [SMS_infrastructure](https://github.com/Single-Molecule-Sequencing/SMS_infrastructure) repository
2. Read the [ONBOARDING.md](https://github.com/Single-Molecule-Sequencing/SMS_infrastructure/blob/main/docs/ONBOARDING.md) guide
3. Explore team projects: [Projects Dashboard](https://github.com/orgs/Single-Molecule-Sequencing/projects)
4. Join relevant team channels and meetings

### For Researchers

1. Cite our preprints and published work
2. Explore the [sms-core-math](https://github.com/Single-Molecule-Sequencing/sms-core-math) registry
3. Use our [interactive calculators](https://github.com/Single-Molecule-Sequencing/SMS_infrastructure) for error estimation
4. Reference our [Golden Gate protocols](https://github.com/Single-Molecule-Sequencing/SMS_infrastructure)

### For Clinicians

1. Review clinical validation data in [paper-singapore-cohort](https://github.com/Single-Molecule-Sequencing/paper-singapore-cohort)
2. Understand CPIC guidelines integration
3. Contact us for pharmacogenomics consultation
4. Explore cost-benefit analysis for clinical implementation

---

## 📖 Publications (In Progress)

### 8 Manuscripts in Development

1. **Empirical Error Rate Determination** (NCRC-BSL1)
2. **Basecalling Optimization** (ML approaches)
3. **Proficiency Testing** (UM-PHI collaboration)
4. **Cas9 Enrichment Analysis**
5. **Singapore Breast Cancer Study** (near submission)
6. **gRNA Optimization** (BSL2)
7. **Human Cell Applications** (BSL2)
8. **Complete SMS Methodology** (BSL2)

---

## 🤝 Join Us

**Principal Investigator**: Dr. Brian D. Athey
**Lab**: University of Michigan, Department of Computational Medicine & Bioinformatics

**Contact**: Visit our website or reach out through GitHub issues

---

## 🏆 Acknowledgments

Supported by:
- University of Michigan Rogel Cancer Center
- National Cancer Centre Singapore
- Phenomics Health Inc.
- NIH/NHGRI grants

---

<div align="center">

**Transforming pharmacogenomics through error-aware, probabilistic sequencing**

[Website](https://atheylabproject.com) • [Documentation](https://github.com/Single-Molecule-Sequencing/SMS_infrastructure) • [Math Registry](https://github.com/Single-Molecule-Sequencing/sms-core-math)

</div>
