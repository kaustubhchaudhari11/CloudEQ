# Text extract: A federated observability architecture pattern for reliable agentic AI.pdf

Extracted mechanically from the original PDF; page markers follow PDF page order.
Original PDF remains authoritative; reading order and tables may be imperfect.


## PDF page 1

A federated observability architecture pattern for reliable agentic AI
software systems across the AI software development lifecycle
Grace Billiris
*
, Asif Gill
University of Technology Sydney, Sydney, New South Wales, Australia
ARTICLE INFO
Keywords:
Multi-agent systems
Federated observability
Data flow
Schema normalisation
Reliability
Agentic AI
Trustworthy AI
AI-driven architecture
ABSTRACT
Context: Multi-agent agentic AI systems generate evolving, and non-deterministic telemetry that reflects
reasoning, decision-making, adaptive workflows, and variable event structures. These systems increasingly
operate across dynamic environments where runtime behaviour and data schemas can change throughout the
phases AI software development lifecycle (SDLC). Traditional observability architectures typically assume fixed
schemas and tightly coupled pipelines, which limits their suitability for adaptive, learning-based AI systems.
Objectives: This paper aims to design and evaluate a Federated Observability Architecture Pattern (FOAP) that
unifies evolving data flows in agentic AI software systems and supports observability, reliability and governance
considerations across the AI SDLC operations.
Methods: We adopt a design science research (DSR) method to design an architecture pattern informed by
established architectural models and standards, including the Data Satellite architecture, the observable agentic
Neuro-Symbolic (ANS) AI system architecture, and ISO/IEC/IEEE 42010. A proof-of-concept prototype was
implemented using synthetic agentic AI workloads to evaluate FOAP feasibility and explore design trade-offs.
Results: The FOAP intends to support schema-agnostic ingestion, raw event retention, semantic normalisation,
and unified storage of heterogeneous telemetry. Comparative analysis existing observability approaches high -
lights its ability to better accommodate schema drift and dynamic agent interactions. Preliminary prototype
evaluation shows that diverse agent-generated events can be preserved and transformed into canonical repre -
sentations suitable for cross-agent analysis under controlled conditions (up to 3 agents generating 110 events).
Conclusion: FOAP provides a structured foundation for improving observability in agentic AI software systems
with heterogeneous and evolving data flows. It offers practical design guidance for AI-driven architectures
integrating adaptive, learning-based components, while supporting reliability, interpretability, and governance-
oriented analysis. Interpretability of agent reasoning is identified as a direction for future work, as the present
prototype evaluates structural and operational observability rather than semantic interpretability of model de -
cisions. Evaluation at large and operational scale remains an important direction for future work.
1. Introduction
Agentic AI systems consist of autonomous agents that plan and
execute tasks, interacting with other agents, digital environments, and
human operators [ 1 – 3 ]. They are increasingly used in AI orchestration,
distributed reasoning, and dynamic tool invocation [ 4 – 6 ]. Their flexi -
bility and growing demand for autonomous workflows enable rapid
adoption [ 1 , 4 ]. As these systems scale, they generate diverse, evolving
data flows – including logs, events, traces, metrics, and intermediate
reasoning tokens – often shaped by differing AI software development
lifecycles (SDLC), runtime adaption, or model evaluation [ 3 , 4 , 7 ]. These
data flows encode internal state (e.g., memory, goals, policies) and
operational context (e.g., inputs, tools, external systems), which results
in frequent schema change.
This heterogeneity fragments system observability, making cross-
agent tasks such as anomaly detection, compliance, auditing explain -
ability and decision support difficult [ 5 , 8 , 9 ]. Reliability in AI systems
refers to consistent, interpretable, and trustworthy system behaviour [ 3 ,
10 – 12 ] that integrates observability, explainability, transparency, and
predictable operations [ 13,14 ]. Existing observability mechanisms as -
sume fixed schemas and are ill-suited for heterogeneous, evolving data
flows in agentic AI systems [ 14 ]. As a result, cross-agent assessment and
* Corresponding author.
E-mail addresses: grace.v.billiris@student.uts.edu.au (G. Billiris), asif.gill@uts.edu.au (A. Gill).
Contents lists available at ScienceDirect
Information and Software Technology
journal homepage: www.elsevi er.com/loc ate/infsof
https://doi.org/10.1016/j.infsof.2026.108260
Received 14 January 2026; Received in revised form 4 June 2026; Accepted 10 July 2026
Information and Software Technology 199 (2026) 108260
Available online 18 July 2026
0950-5849/Crown Copyright © 2026 Published by Elsevier B.V. This is an open access article under the CC BY-NC-ND license
( http://creativecommons.org/licenses/by-nc-nd/4.0/ ).

## PDF page 2

monitoring tasks (e.g., anomaly detection, compliance auditing,
explainability, and decision support) are hindered [ 5 , 8 , 9 ]. Assessing
fairness, accountability, and safety also depends on reliable observations
[ 8 , 15 ].
This gap motivates the key research question addressed in this paper:
How can a federated observability architecture pattern unify evolving
data flows in agentic AI systems to support observability and reliability?
To answer this key research question, we designed a Federated
Observability Architecture Pattern (FOAP) that can handle heteroge -
neous and evolving data flows by incorporating a semantic representa -
tion layer that provides a persistent, structured representation of events
over time. The semantic representation layer supports schema-agnostic
event ingestion, raw trace retention, canonical normalisation, and uni -
fied storage, enabling querying and analysis across agents while
remaining adaptable to different models, operations, and data sources.
A central novelty of FOAP is its dual retention of raw and canonical
events combined with schema-agnostic ingestion, which together pre -
serve emergent telemetry fields while providing a stable analytical
representation – addressing a gap not handled by existing observability
pipelines that assume fixed schemas.
This paper contributes: (1) a novel FOAP design for agentic AI data
flows suitable across the AI SDLC operations, (2) a prototype demon -
strating feasibility of schema-agnostic ingestion with dual raw-canonical
retention, normalisation, and unified storage, and (3) a preliminary
evaluation showing applicability as a foundation for future reference
architectures. The feasibility of the proposed architecture pattern is
evaluated through a proof-of-concept prototype using simulated agentic
AI workloads and data flows that exhibit schema variation and drift.
The rest of this paper is organised as follows: Section 2 reviews
related work, Section 3 presents the research method, Section 4 details
the Federated Observability Architecture Pattern, Section 5 demon -
strates its application through a prototype, Section 6 discusses the re -
sults and implications, and Section 7 concludes with future directions.
2. Background and related work
Before examining specific observability techniques and architec -
tures, it is important to situate the discussion within the broader context
of multi-agent agentic AI systems. Agentic AI systems are characterised
by autonomous decision-making, adaptive workflows, and dynamic in -
teractions between distributed agents [ 6 ]. These characteristics create
highly heterogeneous and evolving multi-agent telemetry streams,
which existing observability methods often cannot fully capture [ 3 , 7 ,
16 ]. This section provides the research motivation based on a review of
literature and related work.
2.1. Observability in distributed and microservice systems
Distributed and cloud-native architectures typically rely on combi -
nations of telemetry data such as logs, metrics, traces, and event streams
for operational monitoring and post-hoc diagnosis [ 3 , 17 ]. Despite ad -
vances in tracing frameworks and high-volume data flow systems,
end-to-end visibility remains difficult to achieve – particularly in
microservice environments where request paths span multiple compo -
nents and fidelity of end-to-end trace correlations (i.e., correctly prop -
agating identifiers and stitching spans across services) degrades under
scale [ 5 , 18 ]. This fragmentation often results in siloed data products
that lack shared semantics, which impedes causal analysis and failure
reconstruction [ 3 , 5 , 18 ], and ultimately leads to AI trust and governance
challenges that motivate the need for federated observability tailored to
agentic AI systems [ 3 , 5 , 18 ].
Existing work highlights the inherent trade-offs between capture fi -
delity, instrumentation overhead, storage cost, and resolution during
trace reconstruction [ 3,18,19 ]. Alternatives such as eBPF-based tracing
offer low-intrusion collection with board system coverage, yet often lack
application-level semantic grounding [ 20 , 21 ]. Recent systems such as
CrossTrace [ 22 ], TraceWeaver [ 23 ] and TraceZip [ 24 ] address
high-volume trace processing through improved stitching, correlation
and compression techniques. However, their holistic observability is
limited by asynchronous execution, dynamic dependency graphs, and
distributed control flows [ 5 , 3 ].
2.2. Observability challenges in agentic AI systems
Agentic AI systems introduce further complexity beyond conven -
tional distributed computing due to autonomous probabilistic behav -
iour, decentralised coordination, and evolving communication protocols
requiring continuous observability [ 3 , 25 , 26 ]. Data flows emitted by
agents may vary in structure, schema, and semantics over time,
complicating lineage reconstruction and intent attribution [ 3 , 26 ].
Standard observability pipelines provide operational visibility but often
cannot capture the reasoning processing or knowledge interactions un -
derlying agent decisions [ 5 , 27 ].
Recent platforms such as LumiMAS and AgentSight extend observ -
ability into agentic environments by incorporating kernel-layer visibil -
ity, behaviour monitoring, and anomaly detection [ 21 , 28 ]. While these
systems advance runtime introspection, they do not provide a systematic
framework for schema-agnostic data flow unification or long-term
provenance retention – capabilities that are essential for semantic in -
spection across heterogeneous agent systems [ 5 , 27 ].
2.3. Governance, auditability, and risk in agentic AI systems
Autonomous AI agents operating in sensitive or mission-critical
contexts require mechanisms for oversight, auditability, and account -
ability [ 8 , 29 ]. Regulatory and organisational governance frameworks
increasingly mandate reconstructability of decision pathways, data
transformations, and tool invocation sequences, necessitating
high-integrity provenance capture [ 5 ]. Sentinel-style monitoring agents
and compliance-oriented runtime controls have been proposed as solu -
tions to constrain behaviour and surface anomalous or policy-violating
activity [ 29 , 30 ].
Observability plays a critical role in supporting trustworthy agentic
AI, as it enables cross-agent lineage reconstruction, post-hoc account -
ability, and provides a substrate for explainability tooling [ 13,15,29 ].
While it is not formally defined as a foundational pillar, these capabil -
ities are widely recognised as necessary for assessing and maintaining
the reliability and transparency of agentic AI systems.
2.4. Federation and shared representations
In agentic environments, fixed-schema approaches are brittle
because message formats, agent goals, and state representations evolve
dynamically [ 19 , 26 ]. Federation mechanisms are necessary when agents
emit unstructured or partially structured events with inconsistent fields,
identifiers, or causal markers [ 3 , 19 ]. Foundational work in data inte -
gration provides theoretical models for unifying distributed sources with
heterogeneous representation [ 31 ].
More recent research on real-time schema and concept drift dem -
onstrates the need to balance raw data preservation with downstream
analytical usability [ 13,32 ]. Emerging proposals – including event reg -
istries and semantic data exchange – argue for shared representation
layers capable of mapping diverse event structures into canonical for -
mats suitable for correlation and analysis [ 3 , 5 , 16 ]. Yet, its utility in
agentic AI observability is not explored in literature.
In summary, existing approaches in distributed systems, micro -
services, and agentic AI either lack semantic unification, cannot reliably
handle heterogeneous or evolving data flows, or do not support long-
term provenance and traceability. These gaps indicate a lack of ap -
proaches that can consistently unify heterogeneous and evolving data
flows while supporting long-term traceability and provenance in agentic
AI systems.
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
2

## PDF page 3

2.5. Conceptual foundations and theoretical lenses
This paper draws on three complementary lenses to motivate and
structure the proposed architecture pattern. We introduce them here to
clarify the conceptual foundations that inform the design choices made
later in the paper.
The first lens is the Data Satellite Architecture (DSA). DSA [ 33 ] is a
conceptual architecture for federated digital ecosystems that emphasises
the ingestion and management of heterogeneous data flows while
explicitly accounting for governance-oriented concerns such as trust -
worthiness, monitoring, and data quality (Data Governance, Quality,
Monitoring and Observability). DSA is relevant to observability in
agentic AI systems because it foregrounds the reality that data originates
from multiple autonomous producers, evolves over time, and often
cannot be forced into a single predefined schema at the point of capture.
In the context of this work, DSA motivates three ideas. First, a layered
decomposition that separates sources, data movement, processing, and
downstream use, which supports evolvability and separation of concerns
in observability pipelines. Second, the need to preserve raw records to
protect against information loss when upstream schemas evolve,
enabling retrospective inspection and reprocessing when mapping rules
or semantics change. Third, the explicit treatment of governance and
monitoring as first-class architectural concerns, rather than as an
afterthought attached to storage or analytics.
The second lens is the Observable Agentic Neuro-Symbolic (ANS) AI
system architecture. ANS AI [ 34 ] frames agentic AI systems as compo -
sitions of interacting neural and symbolic components operating across
multiple layers (e.g., system, environment, human oversight) and
explicitly positions observability as a cross-cutting capability. This lens
is relevant because agentic AI systems generate telemetry that reflects
both conventional execution (e.g., tool calls, message passing) and
agent-specific internal dynamics (e.g., planning steps, intermediate ar -
tefacts), which often evolve as models, tools, and prompts change. For
this paper, ANS motivates treating observability as more than a runtime
monitoring feature: it supports capturing multi-layer signals that enable
interpretation of agent behaviour and system operation. It also moti -
vates the need for representations that support cross-agent correlation
and inspection over time, given that agentic workflows may be
non-deterministic and may change their structure after deployment.
The third lens is the ISO/IEC/IEEE 42010 Architecture Description
Standard. ISO/IEC/IEEE 42010 [ 9 ] is an international standard for
describing software and systems architectures. It provides a vocabulary
and structure for documenting architecture descriptions in terms of
stakeholders, concerns, views/viewpoints, and architectural decisions.
This is relevant in a pattern paper because it encourages making design
choices explicit and traceable, rather than presenting an architecture as
a single diagram without rationale. In this work, ISO/IEC/IEEE 42010
informs how we document the pattern by making the motivation for key
decisions explicit (e.g., schema-agnostic ingestion, dual retention, and
canonicalisation), and by clarifying trade-offs and stakeholder concerns
(e.g., operational monitoring needs versus storage overhead and pro -
cessing complexity). This supports clarity, reproducibility, and inter -
pretability of the proposed pattern.
Building on these concepts, observations and identified gaps, the
following section presents the research method used to systematically
design and evaluate the proposed FOAP.
3. Research method
This paper uses the Design Science Research (DSR) approach [ 35 ,
36 ], following its six stages as illustrated in Fig. 1 , to design and evaluate
a federated observability architecture for agentic AI systems. DSR was
chosen because the research seeks to create and assess a novel artefact
while contributing generalisable design knowledge. Evaluation em -
phasises applicability through a feasibility-oriented proof-of-concept
(POC).
3.1. Problem identification and objectives
As detailed in Section 1 , the key research problem we aim to address
is: How can a federated observability architecture pattern unify evolving
data flows in agentic AI systems to support observability and reliability?
The proposed architecture pattern targets the following design
objectives:
1. Schema-agnostic ingestion of heterogeneous data flows.
2. Retention of raw events to support provenance-oriented inspection.
3. Semantic and structural normalisation into canonical
representations.
4. Cross-agent observability that enables unified querying and analysis.
These objectives are intended to realise a small set of quality prin -
ciples and attributes that directly respond to the gaps identified in
Sections 1 and 2 .
3.2. Artefact design and development
The FOAP was designed and developed iteratively, defining layered
components for ingestion, normalisation, retention, and storage. Three
theoretical lenses guided the design, as described in Section 2.5 .
3.3. Demonstration and evaluation
The pattern was instantiated as a proof-of-concept using simulated
synthetic agentic AI data that capture schema variation and drift. It was
evaluated using operational metrics (throughput, latency, and normal -
isation success) measured for 1 – 3 agents and up to 110 events per
scenario.
For the purposes of this paper, we define the operational metrics as
follows:
• Throughput indicates the number of events successfully ingested per
second, reflecting the architecture's ability to handle concurrent
agent workloads.
• Average latency measures the time (in seconds) from event emission
to availability in the storage and analysis layer, capturing the impact
of federation, normalisation, and dual retention on responsiveness.
Fig. 1. Design Science Research methodology applied to develop the federated
observability pattern.
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
3

## PDF page 4

• Normalisation success is measured as the proportion of ingested
events for which the normaliser produced (i) a syntactically valid
canonical record and (ii) all required canonical fields were populated
(or explicitly marked as missing) according to the canonical schema
used in the prototype.
Our aim was to illustrate feasibility rather than performance at scale.
We also assessed the artefact against DSR-oriented evaluation criteria
(applicability, novelty, generality) [ 37 ] based on how the pattern ad -
dresses the identified gap and how readily the design abstractions
transfer beyond the specific prototype tooling.
3.4. Communication and reflection
The resulting pattern represented in this paper is an initial contri -
bution toward reliable and trustworthy data-flow observability, with
future work focusing on empirical deployment, benchmarking, and
integration into full reference architectures. Design decisions, assump -
tions, and limitations of this work are documented to ensure trans -
parency and reproducibility.
4. Federated observability architecture pattern (FOAP)
Building on this scientific DSR foundation, we introduce FOAP, de -
tailing its conceptual structure, guiding principles, quality attributes,
and the key architectural decisions that operationalise them.
4.1. Conceptual architecture overview
The design of FOAP is guided by the design of the objectives listed in
Section 3.2 . The design separates ingestion, processing, and analysis
concerns to support adaptive and learning-based behaviours, providing
a foundation for traceability, explainability, and governance across the
AI SDLC, shifting a focus from traditional operationally focused
observability to more design driven observability.
Fig. 2 illustrates the high-level architecture pattern we propose,
comprising seven layers, each supporting federated observability and
reliable management of heterogeneous agentic AI system data flows.
Table 1 summaries these layers.
These seven layers, as shown in Fig. 2 and described in Table 1 , are
visually organised using three horizontal bands. The top two horizontal
bands are included for conceptual positioning only, indicating the
complementary foundational theories used to inform the pattern (DSA
and Observable ANS AI). The third horizontal band contains the archi -
tecture itself, showing the seven-layer federated observability pattern
and its supporting components.
This conceptual overview establishes the foundation for under -
standing the pattern. The following subsections outline the architectural
principles, quality attributes, and key decisions that guided its design.
4.2. Architectural principles
FOAP is guided by several interrelated principles that collectively
address the unique challenges of agentic AI systems, drawing on the
theoretical lens [ 33 , 34 ]. At its core, the architecture supports
Fig. 2. Seven-layer Federated Observability Architecture Pattern (FOAP) for agentic AI software systems.
Table 1
Seven layers of FOAP and their purpose.
Layer Purpose
Source
systems
Captures the origins of data flows, including agentic AI systems,
satellites, and external services that produce events. This layer
defines the starting point for monitoring and tracing event
generation.
Source data Represents the individual components within source systems that
generate raw events, logs, or telemetry. It preserves native event
structures and metadata, forming the basis for downstream
federation and analysis.
Streaming Provides real-time ingestion and buffering of heterogeneous data
flows, decoupling event producers from consumers and supporting
reliable delivery to subsequent layers.
Event-driven Orchestrates event movement and routing through the architecture,
enabling structured processing, conditional handling, and traceable
event paths.
Processing Transforms raw events into canonical records via a normalisation
agent, applying field-level semantic extraction, structured error
flagging, and dual retention to enable unified querying and cross-
agent analysis over time.
Storage Persists both raw and normalised events along with operational
metadata, supporting provenance, traceability, retrospective
inspection, and reliable access for analysis.
Analysis Provides querying, monitoring, and visualisation of event data,
supporting operational observability and enabling human
inspection and validation of data flows.
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
4

## PDF page 5

schema-agnostic ingestion, enabling heterogeneous telemetry to be
captured without imposing predefined schemas. This ensures reliability,
extensibility, and traceability, as data streams can evolve independently
of the ingestion pipeline. Complementing this, the pattern employs dual
retention of both raw and canonical events, preserving emergent fields
while providing a stable analytical representation that supports audit -
ability and explainability.
To manage complexity and enable independent evolution of system
components, the architecture embraces layered decoupling, separating
ingestion, processing, and analysis. This modular structure enhances
scalability and performance while allowing each layer to be updated or
extended without disrupting the others. Semantic normalisation further
ensures consistency across heterogeneous telemetry by mapping raw
events to canonical representations, a process that can be supported
through AI-assisted techniques to maintain accuracy and
interpretability.
Observability is extended across all phases of the AI SDLC operations
through cross-phase correlation, allowing training, testing, evaluation,
deployment, and runtime telemetry to be linked and analysed holisti -
cally. This is important for the transparency across the integrated AI
systems that comprise of agents, models, datasets, skills and tools etc.
Dynamic workflows are supported through event-driven orchestration,
which routes events flexibly and scales with system demand. Finally, the
architecture emphasises analysis-driven feedback, providing dashboards
and query interfaces that enable runtime inspection, anomaly detection,
and human-in-the-loop decision support.
Table 2 summarises these principles alongside the associated quality
attributes and key architectural decisions, providing a concise reference
for design and implementation while the narrative here describes the
rationale and interrelationships that underpin the pattern.
These principles naturally define the quality attributes the archi -
tecture must satisfy, providing measurable targets to guide design and
implementation decisions.
4.3. Architectural quality attributes
The federated observability pattern emphasises key quality attri -
butes that operationalise its architectural principles. These selection of
reliability, traceability, explainability, scalability, performance, and
extensibility are grounded in established software architecture evalua -
tion frameworks, which require architecture patterns to be specified and
analysed through explicit non-functional quality attributes to enable
formal reasoning about architectural fitness and trade-offs [ 9 , 38 ]. These
attributes therefore provide a structured basis for evaluating the suit -
ability of the proposed pattern for adaptive, learning-enabled systems.
Within the context of agentic AI systems, these attributes ensure that
the architecture can consistently capture and preserve heterogeneous
telemetry, enable causal reconstruction of agent decisions, support
human-in-the-loop inspection, scale across multiple agents and work -
flows, maintain acceptable latency, and integrate new data sources or
analysis tools with minimal redesign.
With these quality attributes in mind, the next step is to translate
them and the guiding principles into concrete architectural decisions
that operationalise the pattern.
4.4. Architectural decisions
Architectural decisions are defined as the fundamental design
choices that determine a system ’ s structure, behaviour, and evolution by
constraining the selection and configuration of architectural elements,
technologies, and interactions [ 38 , 39 ]. Such decisions capture the
rationale that links quality attribute requirements to concrete architec -
tural structures and are recognised as primary drivers of long-term
system maintainability, scalability, and reliability [ 39 ].
In this paper, architectural decisions translate the identified princi -
ples and quality attributes into concrete and operational design choices.
These include adopting schema-agnostic ingestion, dual retention of raw
and canonical events, layered decoupling of ingestion, processing, and
analysis, semantic normalisation of heterogeneous telemetry, event-
driven orchestration, and unified storage for traceability. Collectively,
these decisions balance flexibility, reliability, and observability in dy -
namic agentic AI systems, enabling consistent cross-phase monitoring,
post-hoc analysis, and governance.
4.5. AI SDLC observability mapping
The proposed pattern is designed to support observability across all
phases of the AI SDLC, as shown in Fig. 3 , through a unified telemetry
ingestion, normalisation, and correlation mechanism that operates
consistently across heterogeneous lifecycle artefacts.
During model training, telemetry capturing instance selection,
hyperparameters, and early decision traces can be ingested through
schema-agnostic interfaces and retained in both raw and canonical
forms. This enables traceability of training configurations and estab -
lishes a foundation for linking model behaviour to upstream data and
parameter choices.
During testing, test outcomes, validation metrics and evaluation logs
can be correlated with training artefacts and agent-related telemetry via
the canonical representation. This supports cross-phase analysis by
enabling relationships to be established between observed system per -
formance and prior development decisions.
During deployment and runtime, real-time agent decisions, adaptive
workflows, and inter-agent interactions are captured, semantically
normalised, allowing for continuous analysis of the system behaviour.
The same canonical model enables these runtime observations to be
linked back to training and testing artefacts, supporting end-to-end
observability.
By maintaining a consistent ingestion and representation strategy
across phases, FOAP supports longitudinal traceability and cross-phase
correlation, allowing events observed at runtime to be contextualised
within earlier stages of the AI SDLC.
With principles, attributes, decisions and AI SDLC observability
mapping clearly articulated, the paper can now demonstrate the pat -
tern ’ s feasibility through the prototype implementation.
Table 2
Architectural principles, quality attributes, and key decisions.
Architectural
principle
Quality attributes Architectural decisions
Schema-agnostic
ingestion
Reliability,
Extensibility,
Traceability
Use decoupled streaming pipelines
to ingest heterogeneous events
without predefined schemas
Dual retention (raw
+ canonical)
Traceability,
Auditability,
Explainability
Store both raw events and
canonical representations in
unified storage
Layered decoupling Modularity,
Scalability,
Performance
Separate ingestion, processing,
and analysis layers to reduce
coupling and support independent
evolution
Semantic
normalisation
Consistency,
Explainability
Map heterogeneous events to
canonical formats using AI-
assisted normalisation
Cross-phase SDLC
observability
Traceability,
Governance
Correlate telemetry across
training, testing, deployment, and
runtime phases
Event-driven
orchestration
Flexibility, Scalability Employ an orchestration engine to
route and process events
dynamically
Analysis-driven
feedback
Maintainability,
Responsiveness
Provide dashboards and query
interfaces for runtime inspection
and anomaly detection
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
5

## PDF page 6

5. Prototype implementation and preliminary evaluation
5.1. Prototype setup
To demonstrate the practical applicability of the federated observ -
ability pattern across the AI SDLC, a proof-of-concept prototype was
implemented using industry standard tools and components as illus -
trated in Fig. 4 .
For this prototype, each layer was instantiated as summarised in
Table 3 .
The Processing Layer warrants additional description as a key
architectural contribution. The normalisation agent was implemented
using the Google Gemini 2.5 Flash API and configured via a structured
system prompt that constrains it to JSON-only output – no explanations,
reasoning, or markdown. This design ensures reliable downstream
parsing regardless of input schema variation. The agent extracts and
normalises fields into a fixed canonical event schema ( Table 4 ), covering
entity identification (actor_entity, target_entity), event classification
event_type, action, job), distributed tracing (span_id, parent_span_id,
task_id), and operational metadata (timestamp, ingestTimestamp, sta -
tus). When telemetry cannot be extracted, the agent sets parseError =
true and success = false, preserving the raw payload for retrospective
inspection. The canonical schema and the normalisation agent prompt
together constitute the semantic representation layer described in
Section 1 .
5.2. Evaluation setup
Evaluation was conducted under a simulated agentic AI system
workload using synthetic data from the Beeceptor API endpoints. Syn -
thetic events were hand-crafted JSON payloads designed to reflect
realistic inter-agent communication and task-execution patterns. Two
Fig. 3. Mapping of federated observability layers to AI SDLC phases.
Fig. 4. Proof-of-concept prototype implementation of the federated observability pattern.
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
6

## PDF page 7

structural variants were used: rich events containing a full set of fields
(e.g., actor_id, target_id, span_d, tool_name, latency_ms, nested meta -
data) and minimal events containing only core identifiers and a status
field. Schema drift was introduced deliberately across runs by renaming
fields (e.g., agent_id to actor_id), adding optional fields (e.g.,
data_size_kb), and omitting fields present in earlier runs, simulating the
kind of gradual schema evolution expected in operational agentic AI
systems. Synthetic data enabled controlled experimentation while
avoiding privacy concerns associated with real-world deployments. The
workload was constrained by Beeceptor free-tier limits (up to 3 con -
current agents and 110 events per scenario), which limits realism and
scale but is sufficient for a feasibility-oriented proof-of-concept.
The three evaluation scenarios vary the following factors:
• Concurrent sources: 1 – 3 agents active simultaneously.
• Event heterogeneity and schema drift: optional fields added,
removed, or renamed across runs, ranging from minimal to rich
event structures.
• Load levels: low, moderate, and high event rates aligned with service
limits.
5.3. Metrics captured
As discussed in Section 3.3 , three operational metrics (throughput,
latency, normalisation success) were captured, highlighting how
increasing agent concurrency and event richness affects processing
performance and normalisation reliability across scenarios.
Representative operational metrics were collected via the Grafana
dashboard ( Fig. 5 ) and are summarised in Table 5 . Direct benchmarking
against state-of-the-art systems such as AgentSight or LumiMAS is not
feasible at this stage, as these systems do not expose comparable nor -
malisation or dual-retention metrics under equivalent workloads; this
remains a direction for future empirical work.
Additionally, the Grafana dashboard supports human-in-the-loop
inspection by allowing users to identify anomalies in event ingestion
or normalisation success, verify canonical mappings, and flag irregular
events, thereby enhancing both cross-phase observability, governance
and auditability.
The results show expected trends under small-scale synthetic work -
loads: throughput decreases and latency increases as agent concurrency
and event complexity grow, reflecting processing overhead for AI-
assisted normalisation and dual retention. Normalisation success
slightly declines for richer and more heterogeneous events, indicating
that automated canonicalisation becomes less reliable as event vari -
ability increases. The decline in normalisation success for richer events
reflects the sensitivity of the LLM-based normalisation agent to prompt-
schema alignment under high event variability, and the throughput
ceiling imposed by the Beeceptor free-tier limits, rather than a funda -
mental scalability constraint of the architecture pattern itself.
The projected scenario anticipates 100 + concurrent agents emitting
a mixture of inter-agent communication events, task-execution logs, and
reasoning traces with active schema drift, requiring horizontally scaled
streaming and parallel normalisation to maintain acceptable throughput
and latency.
These findings demonstrate feasibility under controlled conditions,
rather than operational performance at scale. They provide evidence
that the prototype can support cross-phase observability and governance
in a synthetic environment, while introducing architectural capabilities
not supported by conventional fixed-schema observability pipelines.
5.4. DSR criteria evaluation
The artefact was assessed against DSR-oriented criteria [ 35 , 36 , 40 ]
to clarify its contribution and current limits, as show in Table 6 .
6. Discussion
The evaluation of FOAP highlights several key contributions and
trade-offs when compared with existing observability frameworks. The
pattern was designed to address the limitations of conventional fixed-
schema approaches, particularly in the context of adaptive, learning-
Table 3
Prototype instantiation of each FOAP layer.
Layer Tool / technology Role in prototype
Source
systems
Beeceptor Simulates satellite and agentic AI data
sources.
Source data Two mock telemetry APIs
(via Beeceptor)
Generate rich inter-agent
communication events and minimal
task-execution events to illustrate
heterogeneity.
Streaming Apache Kafka Messaging queues buffer events,
decoupling producers (Beeceptor APIs)
from consumers (downstream layers).
In Fig. 4 , this is represented by the
Kafka Trigger node.
Event-
driven
n8n workflows Workflows route events to processing
or storage, preserving traceability.
Processing Normalisation agent
(Google Gemini 2.5 Flash
API)
Maps heterogeneous raw events into
canonical records using AI-assisted
semantic extraction, applying field-
level rules (e.g., timestamp conversion,
status normalisation, entity
structuring) and setting structured
error flags when extraction fails. Each
event produces both a canonical record
and a retained raw payload, realising
the dual retention objective. In Fig. 4 ,
this is represented by the
Normalisation Agent node.
Storage MongoDB Persists raw and normalised events
with operational metadata. In Fig. 4 ,
this is represented by the MongoDB
node.
Analysis Grafana Loki Visualises event streams and metrics,
supporting human-in-the-loop
inspection.
Table 4
Canonical event schema used in the prototype.
Field Description Group
actor_entity Structured object {entity_type, entity_id}
identifying the initiating agent
Entity
target_entity Entity receiving the action Entity
data_entity Data object involved in the event Entity
destination_entity Downstream target of data or output Entity
human_id Human operator identifier, if present Entity
event_type Normalised event category (lowercase) Classification
action Specific operation performed; defaults to
event_type if absent
Classification
job Derived composite identifier: event_type or
event_type:action
Classification
task_id Task, workflow, or job identifier Traceability
tool_name Name of tool or API invoked Traceability
tool_invocation_id Span, tool call, or invocation identifier Traceability
span_id Distributed trace span identifier Traceability
parent_span_id Parent span for trace correlation Traceability
status Normalised event outcome (uppercase:
SUCCESS, FAILED, ERROR)
Operational
message Human-readable event description Operational
Timestamp Event emission time (ISO 8601 UTC) Operational
ingestTimestamp Time of ingestion into pipeline (ISO 8601
UTC); never null on success
Operational
latency_ms Reported processing latency in milliseconds Operational
data_size_kb Payload size in kilobytes Operational
success Boolean: false if status is FAILED/ERROR or
parseError is true
Control
error_code Error code if applicable ​
parseError Boolean: true if telemetry extraction failed Control
raw Full unmodified original input string Control
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
7

## PDF page 8

enabled multi-agent systems. In this section, we critically analyse the
pattern ’ s novelty, architectural quality attributes, and implications for
observability across the AI SDLC, drawing on both the prototype results
and prior literature.
6.1. Comparison with existing observability approaches
Table 7 contrasts FOAP with representative observability frame -
works and a fixed-schema baseline pipeline reflecting industry ap -
proaches such as OpenTelemetry-style systems and schema-driven
logging.
The baseline assumes predefined ingestion schemas, with non-
conforming events either rejected or partially ingested through trans -
formation and retains only canonical structured data without raw
payload preservation. While suitable for stable microservice environ -
ments, this design is limited in agentic AI systems due to heterogeneous
and evolving telemetry. Under schema drift (e.g., agent_id → actor_id),
events are either rejected or ingested with missing attributes, reducing
semantic fidelity.
FOAP consistently outperforms the baseline across identical syn -
thetic workloads: the baseline discards non-conforming attributes and
fails under schema drift, whereas FOAP's schema-agnostic ingestion
with dual retention of raw and canonical events preserves full trace -
ability and enables retrospective cross-agent analysis.
Table 7 adopts a feature-level comparison rather than a cross-system
quantitative benchmark. While internal metrics (throughput, latency,
normalisation success) were captured and are reported in Table 3 , cross-
system comparison is not currently feasible. No standardised benchmark
datasets or shared evaluation protocols exist for agentic AI observability,
and the closest comparators – AgentSight [ 28 ] and LumiMAS [ 21 ] –
operate at different abstraction levels and do not expose comparable
metrics under equivalent workloads. Within the DSR method, an
exploratory evaluation strategy can be used for early-stage artefact
validation [ 35 , 36 , 40 ].
A rigorous future benchmark would require: (i) a shared standard of
heterogeneous agentic AI telemetry with controlled schema-drift sce -
narios, (ii) standardised metrics for normalisation accuracy, throughput,
latency, and storage overhead, and (iii) reproducible baseline
Fig. 5. Example dashboards for runtime analysis of federated observability data.
Table 5
Prototype metrics observed (small-scale agentic AI system).
Scenario Throughput
(events/s)
Avg
latency (s)
Normalisation
success (%)
1 agent, minimal
events
12 8.5 100
2 agents, mixed events 5 15.2 93.3
3 agents, rich events 4 22 90
(Projected) 100 agents,
mixed events †
50 - – 200* 30 - – 60* 75 - – 85*
† Projected values based on architectural analysis assuming horizontal scaling of
streaming and processing layers (e.g., partitioned message queues, parallel
normalisation agents). * denotes estimated ranges, not measured values. Actual
performance will depend on deployment infrastructure, LLM provider
throughput limits, and event schema complexity.
Table 6
Exploratory design science evaluation of the FOAP artefact.
DSR criterion Definition Evaluation
approach
Observed outcome
Applicability
(exploratory)
Ability to operate
across AI SDLC
phases
SDLC telemetry
mapping and
tracing in
prototype
Successful ingestion
and correlation
across training,
testing, and runtime
telemetry. Supports
human inspection
under small-scale
workloads.
Generalisability
(exploratory)
Ability to ingest
heterogeneous
telemetry
schemas
Synthetic
agents with
varying event
structures
Heterogeneous
schemas ingested
without pipeline
modification.
Layered design
indicates
transferability;
large-scale
validation remains
future work.
Novelty Architectural
differentiation
from fixed-
schema pipelines
Comparative
feature analysis
Introduces schema-
agnostic ingestion
and dual retention in
a reusable layered
pattern. Dual
retention not
supported by
baseline approaches.
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
8

## PDF page 9

implementations under identical conditions.
6.2. Architectural decisions and trade-offs
Using the ISO/IEC/IEEE 42010 [ 9 ] framework as a guiding lens,
Table 8 summarises key architectural decisions in terms of stakeholders,
concerns, alternatives, chosen approach and trade-offs. This formalised
rationale makes our design decision-making explicit and traceable. It
also highlights areas where alternative choices may be appropriate in
different deployment contexts.
6.3. Implications for AI SDLC observability
While FOAP architecturally supports observability across all AI SDLC
phases ( Fig. 3 ), the prototype evaluation prioritised deployment and
runtime telemetry as the initial demonstration target. This was a
deliberate scoping decision: runtime observability represents the phase
where schema heterogeneity, agent autonomy, and non-deterministic
behaviour converge most acutely, and where the pattern's core contri -
butions – schema-agnostic ingestion, semantic normalisation, and dual
retention – are most immediately testable. The evaluation confirmed
that the prototype successfully ingests, normalises, and retains hetero -
geneous runtime telemetry from multiple concurrent agents ( Section
5.2 ), with Grafana dashboards supporting real-time human-in-the-loop
inspection ( Fig. 5 ).
For the training phase, the prototype's Streaming and Storage Layers
are architecturally capable of ingesting telemetry events tagged with
training-phase metadata (e.g., hyperparameter configurations, instance
selection decisions), as the schema-agnostic pipeline imposes no struc -
tural constraints on event content. However, the current implementa -
tion does not yet include dedicated ingestion connectors to model
training frameworks (e.g., MLflow, Weights & Biases). Realising full
training-phase observability would require such adapters alongside
normalisation rules tailored to training-specific event schemas.
Similarly, for the testing and evaluation phase, the architecture
supports ingestion of test outcome events and validation metrics
through the same schema-agnostic pipeline. Extending the prototype
with CI/CD pipeline connectors (e.g., integration with Kubeflow Pipe -
lines or GitHub Actions telemetry) and test-specific canonical schema
extensions would operationalise this capability.
These gaps do not reflect architectural limitations but rather the
expected scope of an initial DSR feasibility evaluation [ 35 , 36 ]. Runtime
was prioritised because it presents the greatest observability challenge
for agentic AI systems and provides the strongest test of FOAP's differ -
entiating capabilities. The SDLC mapping ( Fig. 3 ) and architectural
principles ( Table 2 ) establish the structural foundation; progressive
integration with phase-specific toolchains constitutes a concrete and
tractable next step for empirical validation.
6.4. Limitations and future work
This paper demonstrates feasibility rather than operational perfor -
mance at scale. The evaluation used synthetic workloads limited to 3
agents and 110 events per scenario, constraining realism and concur -
rency. Direct benchmarking against existing agentic AI observability
systems (e.g., AgentSight, LumiMAS) is constrained by the absence of
shared evaluation protocols and comparable metric definitions across
systems; conclusions are therefore scoped to conceptual validation. The
observed decline in normalisation success under higher event variability
is best understood as an infrastructure and model limitation rather than
a fundamental scalability constraint of the architecture pattern. The
layered, decoupled design means ingestion, normalisation, and storage
components can be scaled or substituted independently – for example,
replacing the normalisation agent with a higher-capacity model or a
hybrid rule-based approach – without redesigning the pattern.
The use of a large language model for semantic normalisation in -
troduces risks beyond the normalisation success decline reported in
Table 5 . First, hallucination: the LLM may generate plausible but
factually incorrect canonical field values – for example, inferring an
event_type or actor_entity that does not correspond to the raw payload.
In observability contexts, such errors could produce misleading
Table 7
Comparison of the Federated Observability Architecture Pattern (FOAP) with
baseline and existing approaches.
Feature Fixed-schema baseline
(e.g. OpenTelemetry-
style pipelines)
Existing systems
(e.g. AgentSight,
LumiMAS)
Proposed
pattern
Schema-agnostic
ingestion
No Partial Yes
Handling of
schema drift
Limited (ingestion
failure or data loss)
Partial Yes
Dual retention
(raw +
canonical)
No No Yes
End-to-end AI
SDLC support
No No Yes
Cross-agent
semantic
normalisation
No Partial Yes
Support for
adaptive,
learning-based
agents
No No Yes
Governance and
auditability
focus
Limited Limited Explicit
Table 8
Architectural decisions and trade-offs in FOAP using the ISO/IEC/IEEE 42010 lens [ 9 ] .
Decision Stakeholders Alternatives Chosen approach Quality
attributes
Trade-offs
Schema-agnostic
ingestion
Developers,
system integrators
Predefined schemas; semi-
structured ingestion
Accept heterogeneous events
without predefined schemas
Extensibility
Scalability
Performance
Shifts responsibility for schema variation to
downstream components; increases
processing complexity
Dual retention of raw
and canonical forms
Analysts, auditors Store only canonical; discard
raw
Retain both raw and
canonical events
Reliability
Traceability
Explainability
Additional storage overhead; lifecycle
management complexity; supports
provenance and replay
Distributed event
backbone
DevOps, operators Centralised ingestion; direct
source-to-consumer pipelines
Kafka-based decoupled event
backbone
Scalability
Reliability
Performance
Operational cost and coordination
overhead; enables resilience and scalable
event delivery
AI-assisted semantic
normalisation
Data engineers,
analysts
Rule-based normalisation;
manual mappin
LLM-assisted normalisation
for heterogeneous events
Explainability
Traceability
Explainability
Potential variability in output quality;
requires monitoring and human-in-the-loop
checks
Unified canonical event
model
Analysts, system
architects
Multiple agent-specific
schemas; flat unstructured
storage
Single extensible canonical
schema
Traceability
Extensibility
Explainability
Schema evolution must be managed
carefully; risk of constraining future
extensions
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
9

## PDF page 10

dashboards or mask genuine anomalies. Second, semantic drift: as the
underlying model is updated by its provider, output formats and
extraction behaviours may change, causing previously reliable normal -
isation mappings to degrade without explicit notification. Third, non-
determinism: identical raw events may produce subtly different canon -
ical representations across invocations due to the stochastic nature of
LLM inference, complicating reproducibility and regression testing.
Fourth, governance and auditability: reliance on an opaque, externally
hosted model raises concerns about the traceability and verifiability of
AI-generated data transformations, particularly in regulated domains
subject to emerging AI governance frameworks [ 15 , 41 ].
The prototype partially mitigates these risks through structured
prompting constrained to JSON-only output, explicit parseError flagging
when extraction fails, dual retention of raw events as a safety net for
retrospective correction ( Section 4.2 ), and human-in-the-loop validation
via the Analysis Layer (Grafana dashboards). Nevertheless, these miti -
gations are partial. Future enhancements should include formal vali -
dation frameworks, confidence scoring for normalised fields (e.g., per-
field extraction probability estimates or agreement metrics across mul -
tiple inference passes), and automated semantic-drift detection mecha -
nisms that compare normalisation outputs against versioned baseline
mappings.
A related concern is the reproducibility implications of using a pro -
prietary, cloud-hosted model (Google Gemini 2.5 Flash) for the nor -
malisation agent. This choice was driven by practical considerations:
Gemini 2.5 Flash offers strong instruction-following capabilities, reli -
able structured JSON output, and low-latency inference suitable for
event-driven processing – all critical requirements for the Processing
Layer as described in Section 5.1 . However, dependence on a proprietary
API introduces risks around cost variability, service availability, and the
inability for third-party researchers to reproduce experiments under
identical model conditions.
Critically, the architecture's layered decoupling ( Section 4.2 ) means
the normalisation agent is a swappable component within the Processing
Layer. The normalisation interface requires only that the substituted
model can: (i) accept a structured prompt with a raw telemetry payload,
(ii) produce valid JSON output conforming to the canonical schema
( Table 4 ), and (iii) set error flags when extraction fails. Open-source
models such as Llama 3, Mixtral or Phi-3 increasingly demonstrate
these capabilities – particularly structured JSON generation and
instruction-following – and could serve as alternative instantiations of
the normalisation component. Evaluating open-source alternatives
across the normalisation accuracy, throughput, and latency dimensions
observed in Table 5 is planned as future work. Such evaluation would
also enable fully reproducible experimental configurations, addressing
the legitimate concern that proprietary model dependence limits the
verifiability of our reported results.
Key trade-offs remain: dual retention ensures traceability but in -
creases storage overhead, suggesting hybrid or tiered strategies at scale;
event-driven streaming improves resilience but adds latency that may
affect near-real-time monitoring; and AI-assisted normalisation requires
ongoing monitoring to maintain trustworthiness. Future work will
evaluate performance under larger deployments and higher event vol -
umes, explore alternative normalisation models, extend the Analysis
Layer with automated reasoning and anomaly detection, pursue real-
world validation in operational multi-agent systems, and integrate
governance and compliance mechanisms.
7. Conclusion
This paper introduces a federated observability architecture pattern
(FOAP) for agentic AI systems, addressing the challenge of unifying
heterogeneous, evolving events from multiple autonomous agents to
support observability and reliability. The layered FOAP enables schema-
agnostic ingestion, raw event retention, semantic normalisation, and
unified storage, preserving traceability and supporting auditability.
A proof-of-concept FOAP prototype demonstrates that heteroge -
neous data flows can be ingested, retained in raw form, and transformed
into canonical representations for analysis under controlled, small-scale
conditions. Preliminary evaluation confirms that ingestion, normal -
isation, and storage function as intended and support human-in-the-loop
inspection.
The contributions include a reusable architecture pattern, design
principles for handling evolving agentic data, and a prototype validating
feasibility. This work provides a practical foundation for traceable, dual-
retention, and semantically coherent observability in agentic AI systems.
FOAP extends conventional observability paradigms to learning-based
agentic systems and provides a scalable architectural foundation for
observability across the AI software development lifecycle.
Future work will evaluate the pattern at larger scale, integrate
automated monitoring and AI-assisted reasoning for anomaly detection,
and document lessons to guide broader adoption.
CRediT authorship contribution statement
Grace Billiris: Writing – original draft, Visualization, Validation,
Software, Resources, Project administration, Methodology, Investiga -
tion, Formal analysis. Asif Gill: Writing – review & editing, Supervision.
Declaration of competing interest
The authors declare the following financial interests/personal re -
lationships which may be considered as potential competing interests:
Grace Billiris reports financial support was provided by Australian
Government Research Training Program. If there are other authors, they
declare that they have no known competing financial interests or per -
sonal relationships that could have appeared to influence the work re -
ported in this paper.
Acknowledgement
This research is supported by an Australian Government Research
Training Program Scholarship. The authors gratefully acknowledge this
support, which as aided the completion of this paper.
Data availability
No data was used for the research described in the article.
References
[1] S. Mehta, Autonomous AI agents for personalized financial negotiation in consumer
banking, Res. Square (2025) .
[2] V. Tupe, S. Thube, AI agentic workflows and enterprise APIs: adapting API
architectures for the age of AI agents, TechRxiv (2025) .
[3] R. Souza, A. Gueroudji, S. DeWitt, D. Rosendo, T. Ghosal, R. Ross, P. Balaprakash,
R. Ferreira da Silva, PROV-AGENT: Unified Provenance for Tracking AI Agent
Interactions in Agentic Workflows, arXiv (2025), https://doi.org/10.48550/
arXiv.2508.02866.
[4] K.A. Patel, I. Misra, E.C. Pandey, R. Singh, A. Sharma, Agentic AI for cloud
troubleshooting: a review of multi-agent system for automated cloud support, in:
Proc. 2025 Int. Conf. Inventive Computation Technologies, IEEE, 2025,
pp. 422–428 .
[5] S. Raza, R. Sapkota, M. Karkee, C. Emmanouilidis, TRiSM for agentic AI: a review
of trust, risk, and security management in LLM-based agentic multi-agent systems,
arXiv preprint (2025). arXiv:2506.04133 .
[6] T. Joshi, D. Gala, Architecting agentic AI for modern software testing: capabilities,
foundations, and a proposed scalable multi-agent system for automated test
generation, in: Proc. IEEE Int. Conf. Softw. Test., 2025 .
[7] D. Katasani, Federated learning with AI agents across multi-cloud data platforms,
Eur. Modern Stud. J. 9 (2025) 668–678 .
[8] A. Nikiforova, M. Lnenicka, U. Melin, D. Valle-Cruz, A.Q. Gill, C. Casiano Flores,
E. Sirait, M. Luterek, R.M. Dreyling, B. Tesarova, Responsible AI adoption in the
public sector: a data-centric taxonomy of AI adoption challenges, in: Proc. 59th
Hawaii Int. Conf. Syst. Sci. (HICSS), 2025, pp. 1–10 .
[9] ISO/IEC/IEEE, Systems and software engineering – architecture description, 2011.
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
10

## PDF page 11

[10] A. Oyeronke, Y. Quadry, Toward trustworthy AI: navigating risk and ensuring
privacy in cloud-telecom systems with federated learning, Future Gener. Comput.
Syst. (2025) .
[11] H. Ijaiya, Harnessing AI for data privacy: risks and opportunities, Int. J. Sci. Res.
Arch. 13 (2024) 2878–2892 .
[12] B. Li, X. Peng, Q. Xiang, H. Wang, T. Xie, J. Sun, X. Liu, Enjoy your observability:
an industrial survey of microservice tracing and analysis, Empir. Softw. Eng. 27
(2022) 1–28, https://doi.org/10.1007/s10664-021-10063-9.
[13] P. Zambare, V.N. Thanikella, Y. Liu, Securing agentic AI: threat modeling and risk
analysis for network monitoring agentic AI system (MAESTRO), arXiv preprint
(2025). arXiv:2508.10043 .
[14] R. Bohnsack, M. de Wet, AI is the strategy: from agentic AI to autonomous business
models, arXiv preprint (2025). arXiv:2506.17339 .
[15] A. Batool, D. Zowghi, M. Bano, Responsible AI governance: a systematic literature
review, Inf. Softw. Technol. (2025) .
[16] K. Kalodanis, G. Feretzakis, A. Anastasiou, P. Rizomiliotis, D. Anagnostopoulos,
Y. Koumpouros, A privacy-preserving and attack-aware AI approach for high-risk
healthcare systems under the EU AI Act, Electronics 14 (2025) 1385 .
[17] M. Panahandeh, A. Hamou-Lhadj, M. Hamdaqa, J. Miller, ServiceAnomaly: an
anomaly detection approach in microservices using distributed traces and profiling
metrics, J. Syst. Softw. 209 (2024) 111917, https://doi.org/10.1016/j.
jss.2023.111917.
[18] S.K. Pamarthy, AI-powered PII data discovery and protection: a comprehensive
analysis, Int. J. Comput. Eng. Technol. 16 (2025) 3301–3315 .
[19] E. Kandogan, N. Bhutani, D. Zhang, R.L. Chen, S. Gurajada, E. Hruschka,
Orchestrating agents and data for enterprise: a blueprint architecture for
compound AI, arXiv (2025), https://doi.org/10.48550/arXiv.2504.08148.
[20] W. Yang, P. Chen, K. Liu, H. Zhang, Nahida: in-band distributed tracing with eBPF,
arXiv preprint (2023). arXiv:2311.09032 .
[21] R. Solomon, Y.Y. Levi, L. Vaknin, E. Aizikovich, A. Baras, E. Ohana, A. Giloni,
S. Bose, C. Picardi, Y. Elovici, A. Shabtai, LumiMAS: a comprehensive framework
for real-time monitoring and enhanced observability in multi-agent systems, arXiv
preprint (2025). arXiv:2508.12412 .
[22] L.-A. Phan, CrossTrace: efficient cross-thread and cross-service span correlation in
distributed tracing for microservices, arXiv preprint (2025). arXiv:2508.11342 .
[23] K. Ashok, TraceWeaver: distributed request tracing for microservices without
application modification, in: Proc. ACM SIGCOMM, 2024 .
[24] Z. Chen, J. Pu, Z. Zheng, TraceZip: efficient distributed tracing via trace
compression, arXiv preprint (2025). arXiv:2502.06318 .
[25] P.S. Viswanathan, Agentic AI: a comprehensive framework for autonomous
decision-making systems in artificial intelligence, Int. J. Comput. Eng. Technol. 16
(2025) 862–879 .
[26] N. Krishnan, Advancing multi-agent systems through model context protocol:
architecture, implementation, and applications, arXiv preprint (2025), https://doi.
org/10.48550/arXiv.2504.21030.
[27] N. Kshetri, J. Voas, Agentic artificial intelligence for cyber threat management,
IEEE Computer 58 (5) (2025) 86–90 .
[28] Y. Zheng, Y. Hu, T. Yu, A. Quinn, AgentSight: system-level observability for AI
agents using eBPF, arXiv preprint (2025). arXiv:2508.02736 .
[29] D. Gosmar, D.A. Dahl, Sentinel agents for secure and trustworthy agentic AI in
multi-agent systems, arXiv preprint (2025). arXiv:2509.14956 .
[30] C.L. Wang, T. Singhal, A. Kelkar, J. Tuo, MI9 – Agent intelligence protocol: runtime
governance for agentic AI systems, arXiv preprint (2025), https://doi.org/
10.48550/arXiv.2508.03858.
[31] M. Lenzerini, Data integration: a theoretical perspective, in: Proc. PODS, 2002,
pp. 233–246 .
[32] S. Wares, J. Isaacs, E. Elyan, Data stream mining: methods and challenges for
concept drift, SN Appl. Sci. 1 (2019) 1412 .
[33] A.Q. Gill, A. Nikiforova, Towards a data satellite architecture for federated digital
ecosystems, in: CAiSE, Springer, 2025, https://doi.org/10.1007/978-3-031-94590-
8_12.
[34] Gill A.Q., Zhang Y., Designing an observable human-centric agentic AI system
architecture for decision-making, 2025.
[35] A.R. Hevner, S.T. March, J. Park, S. Ram, Design science in information systems
research, MIS Q. 28 (2004) 75–105 .
[36] K. Peffers, T. Tuunanen, M. Rothenberger, S. Chatterjee, A design science research
methodology for information systems research, J. Manag. Inf. Syst. 24 (2007)
45–77 .
[37] L. Sun, Y. Yang, Q. Duan, Y. Shi, C. Lyu, Y.-C. Chang, C.-T. Lin, Y. Shen, Multi-agent
coordination across diverse applications: a survey, arXiv preprint (2025). arXiv:2
502.14743 .
[38] L. Bass, P. Clements, R. Kazman, Software Architecture in Practice, 4th ed., 2021 .
[39] Kruchten P., Lago P., van Vliet H., An ontology of architectural design decisions, in:
Proc. 2nd Groningen Workshop on Software Variability Management, 2004.
[40] C. Sonnenberg, J. vom Brocke, Evaluation Patterns For Design Science Research
Artefacts, Springer LNCS, 2012, pp. 71–83 .
[41] A. Chan, et al., Visibility into AI agents, in: Proc. ACM Conf. Fairness,
Accountability, and Transparency, 2024 .
G. Billiris and A. Gill                                                                                                                                                                                                                           Information and Software Technology 199 (2026) 108260
11
