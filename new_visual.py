import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import random
from collections import Counter, defaultdict
import numpy as np
import math

df = pd.read_csv("Final_Combined.csv")

def fix_coauthors(x):
    if pd.isna(x):
        return []
    x = x.strip("[]")
    if x == "":
        return []
    return [name.strip().strip("'").strip('"') for name in x.split(",")]

df["coauthors"] = df["coauthors"].apply(fix_coauthors)

def sample_authors_by_seed(participants_set, fraction=0.75, seed=42):
    participants_list = list(participants_set)
    random.seed(seed)
    num_to_select = int(len(participants_list) * fraction)
    return set(random.sample(participants_list, num_to_select))

def build_one_year_network(df, group, paper_year, sampled_participants=None):

    subset = df[(df["group"] == group) & (df["paper_year"] == paper_year)]

    if sampled_participants is not None:
        subset = subset[subset["author_name"].isin(sampled_participants)]

    participants = set(subset["author_name"].unique())

    # Count number of papers per participant
    paper_counts = Counter(subset["author_name"])

    # Count coauthor ties edge weights
    edge_counter = Counter()
    all_authors = set()

    for _, row in subset.iterrows():
        author = row["author_name"]
        coauthors = row["coauthors"]

        all_authors.add(author)
        all_authors.update(coauthors)

        for co in coauthors:
            edge = tuple(sorted([author, co]))
            edge_counter[edge] += 1

    G = nx.Graph()
    G.add_nodes_from(all_authors)

    for (a, b), w in edge_counter.items():
        G.add_edge(a, b, weight=w)

    return G, participants, paper_counts

def plot_network(G, participants, paper_counts, title, filename):

    plt.figure(figsize=(14, 12))

    participants = set(participants)
    coauthors = set(G.nodes()) - participants

    pos = {}

    n_outer = len(participants)
    radius_outer = 4.0

    angles = np.linspace(0, 2 * math.pi, n_outer, endpoint=False)
    for node, angle in zip(sorted(participants), angles):
        pos[node] = np.array([
            radius_outer * math.cos(angle),
            radius_outer * math.sin(angle)
        ])

    inner_radius = radius_outer * 0.85

    for node in coauthors:
        r = inner_radius * np.sqrt(np.random.rand())   # uniform in disk
        theta = 2 * math.pi * np.random.rand()

        pos[node] = np.array([
            r * math.cos(theta),
            r * math.sin(theta)
        ])

    node_colors = [
        "red" if node in participants else "lightblue"
        for node in G.nodes()
    ]

    node_sizes = []
    for node in G.nodes():
        if node in participants:
            node_sizes.append(paper_counts.get(node, 1) * 300)
        else:
            node_sizes.append(80)

    edge_widths = [
        G[u][v]["weight"] * 0.4 for u, v in G.edges()
    ]

    nx.draw_networkx_nodes(
        G,
        pos,
        node_color=node_colors,
        node_size=node_sizes,
        alpha=0.85
    )

    nx.draw_networkx_edges(
        G,
        pos,
        width=edge_widths,
        alpha=0.25
    )

    labels = {node: node for node in participants}
    nx.draw_networkx_labels(G, pos, labels, font_size=6)

    plt.title(title, fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(filename, format="jpg", dpi=300)
    plt.close()

    print(f"Saved: {filename}")

def network_summary(G, participants):
    return {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "avg_degree": sum(dict(G.degree()).values()) / G.number_of_nodes() if G.number_of_nodes() > 0 else 0,
        "density": nx.density(G),
        "unique_coauthors": len(set(G.nodes()) - set(participants)),
        "cluster_coefficient": nx.average_clustering(G)
    }

treatment_authors = set(df[df["group"] == "treatment"]["author_name"].unique())
control_authors = set(df[df["group"] == "control"]["author_name"].unique())

SAMPLED_SEED = 35
fraction = 1

sampled_treatment = sample_authors_by_seed(treatment_authors, fraction, SAMPLED_SEED)
sampled_control = sample_authors_by_seed(control_authors, fraction, SAMPLED_SEED)


print("- Starting Network Analysis (All Authors) -")

network_specs_sampled = [
    ("treatment", 2017, "different_network_treatment_pre_datathon.jpg"),
     ("control",    2017, "differentL_network_control_pre_datathon.jpg"),
     ("treatment", 2023, "different_network_treatment_post_datathon.jpg"),
     ("control",    2023, "different_network_control_post_datathon.jpg"),
]

for cohort, year, file in network_specs_sampled:
    sampled_authors = sampled_treatment if cohort == "treatment" else sampled_control

    G, participants, paper_counts = build_one_year_network(
        df, cohort, year, sampled_authors
    )

    title = f"{cohort.capitalize()} Cohort Coauthor Network ({year}, {fraction * 100}% Sampled)"

    plot_network(G, participants, paper_counts, title, file)

    summary = network_summary(G, participants)
    print(f"- {cohort.capitalize()} {year} SAMPLED Network Summary -")
    for k, v in summary.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")



