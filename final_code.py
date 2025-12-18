import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict

df = pd.read_csv("Final_Combined.csv")


def fix_coauthors(x):
    if pd.isna(x): 
        return []
    # Remove brackets and split
    x = x.strip("[]")
    if x == "":
        return []
    return [name.strip().strip("'").strip('"') for name in x.split(",")]

df["coauthors"] = df["coauthors"].apply(fix_coauthors)



def build_one_year_network(df, group, paper_year):
    
    subset = df[(df["group"] == group) & (df["paper_year"] == paper_year)]
    
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
    
    # Build graph
    G = nx.Graph()
    G.add_nodes_from(all_authors)
    G.add_edges_from(edges)
    
    return G, participants, all_authors


def plot_network(G, participants, title, filename):
    plt.figure(figsize=(14, 12))

    # increase spacing between nodes with higher k
    pos = nx.spring_layout(G, seed=42, k=0.6, iterations=200)

    # add color participants vs others
    color_map = ['red' if node in participants else 'lightblue' for node in G.nodes()]

    # node size = degree coauthors so important nodes stand out
    degree_dict = dict(G.degree())
    node_sizes = [max(degree_dict[n] * 50, 80) for n in G.nodes()]  # minimum size 80

    # draw nodes and edges more cleanly
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

network_specs = [
    ("treatment", 2017, "network_treatment_pre_datathon.jpg"),
    ("control",    2017, "network_control_pre_datathon.jpg"),
    ("treatment", 2023, "network_treatment_post_datathon.jpg"),
    ("control",    2023, "network_control_post_datathon.jpg"),
]

for cohort, year, file in network_specs:
    G, participants, all_nodes = build_one_year_network(df, cohort, year)
    title = ""
    if year == 2017:
        title = f"{cohort.capitalize()} Cohort Coauthor Network (Pre Datathon)"
    else:
        title = f"{cohort.capitalize()} Cohort Coauthor Network (Post Datathon)"
    plot_network(G, participants, title, file)

def network_summary(G, participants):
    num_nodes = G.number_of_nodes()
    num_edges = G.number_of_edges()
    
    # Average degree
    if num_nodes > 0:
        avg_degree = sum(dict(G.degree()).values()) / num_nodes
    else:
        avg_degree = 0
    
    # Network density
    density = nx.density(G)
    
    # Average Clustering Coefficient
    avg_clustering = nx.average_clustering(G)
    
    # Number of unique coauthors excluding participants
    unique_coauthors = len(set(G.nodes()) - set(participants))
    
    summary = {
        "num_nodes": num_nodes,
        "num_edges": num_edges,
        "avg_degree": avg_degree,
        "density": density,
        "unique_coauthors": unique_coauthors,
        "clustering coefficient": avg_clustering
    }
    return summary


network_specs = [
    ("treatment", 2017, "network_treatment_2017.jpg"),
    ("control",    2017, "network_control_2017.jpg"),
    ("treatment", 2023, "network_treatment_2023.jpg"),
    ("control",    2023, "network_control_2023.jpg"),
]

for cohort, year, file in network_specs:
    G, participants, all_nodes = build_one_year_network(df, cohort, year)
    
    # Plot network
    title = f"{cohort.capitalize()} Cohort Coauthor Network ({year})"
    plot_network(G, participants, title, file)
    
    # Compute & print network summary
    summary = network_summary(G, participants)
    print(f"{cohort.capitalize()} {year} Network")
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"{k}: {v:.4f}")
        else:
            print(f"{k}: {v}")