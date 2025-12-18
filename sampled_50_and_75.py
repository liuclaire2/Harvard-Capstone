import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import random

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
    sampled_authors = random.sample(participants_list, num_to_select)
    return set(sampled_authors)


def build_one_year_network(df, group, paper_year, sampled_participants=None):
    
    subset = df[(df["group"] == group) & (df["paper_year"] == paper_year)]
    
    if sampled_participants is not None:
        subset = subset[subset["author_name"].isin(sampled_participants)]
    
    participants = set(subset["author_name"].unique()) 
    
    edges = []
    all_authors = set()

    for _, row in subset.iterrows():
        author = row["author_name"]
        coauthors = row["coauthors"]
        
        all_authors.add(author)
        all_authors.update(coauthors)
        
        for co in coauthors:
            edges.append((author, co))
    
    G = nx.Graph()
    G.add_nodes_from(all_authors)
    G.add_edges_from(edges)
    
    return G, participants, all_authors


def plot_network(G, participants, title, filename):
    plt.figure(figsize=(14, 12))
    pos = nx.spring_layout(G, seed=42, k=1, iterations=300)
    stretch_factor = 1.5 
    for node, coords in pos.items():
        if node in participants:
            coords[0] = coords[0] * stretch_factor
            coords[1] = coords[1] * stretch_factor
            pos[node] = coords
            
    color_map = ['red' if node in participants else 'lightblue' for node in G.nodes()]
    degree_dict = dict(G.degree())
    node_sizes = [max(degree_dict.get(n, 0) * 50, 80) for n in G.nodes()] 

    nx.draw_networkx_nodes(G, pos, 
                           node_color=color_map, 
                           node_size=node_sizes, 
                           alpha=0.85)
    nx.draw_networkx_edges(G, pos, 
                           alpha=0.15, 
                           width=0.5)

    labels = {node: node for node in G.nodes() if node in participants} 
    nx.draw_networkx_labels(G, pos, labels, font_size=6)

    plt.title(title, fontsize=16)
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(filename, format="jpg", dpi=300)
    plt.close()
    print(f"Saved: {filename}")


def network_summary(G, participants):
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    
    if num_nodes > 0:
        avg_degree = sum(dict(G.degree()).values()) / num_nodes
    else:
        avg_degree = 0
    
    density = nx.density(G)
    unique_coauthors = len(set(G.nodes()) - set(participants))
    
    summary = {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "avg_degree": avg_degree,
        "density": density,
        "unique_coauthors": unique_coauthors
    }
    return summary


treatment_authors = set(df[df["group"] == "treatment"]["author_name"].unique())
control_authors = set(df[df["group"] == "control"]["author_name"].unique())

SAMPLED_SEED = 35
sampled_treatment = sample_authors_by_seed(treatment_authors, fraction=0.75, seed=SAMPLED_SEED)
sampled_control = sample_authors_by_seed(control_authors, fraction=0.75, seed=SAMPLED_SEED)

network_specs_sampled = [
    ("treatment", 2017, "75sampled_75_network_treatment_2017.jpg"),
    ("control",    2017, "75sampled_75_network_control_2017.jpg"),
    ("treatment", 2023, "75sampled_75_network_treatment_2023.jpg"),
    ("control",    2023, "75sampled_75_network_control_2023.jpg"),
]

#debug
#print("- Starting Sampled Network Analysis (75% of Authors) -")

for cohort, year, file in network_specs_sampled:
    sampled_authors = sampled_treatment if cohort == "treatment" else sampled_control
    
    G, participants, all_nodes = build_one_year_network(df, cohort, year, sampled_authors)
    
    title = f"{cohort.capitalize()} Cohort Coauthor Network ({year}, 75% Sampled)"
        
    plot_network(G, participants, title, file)
    
    summary = network_summary(G, participants)
    print(f"- {cohort.capitalize()} {year} SAMPLED Network Summary -")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")