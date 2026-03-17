#!/usr/bin/env python3
"""
Generate architecture diagrams for EnvisionPerdido using the `diagrams` library.

Outputs PNG files to docs/diagrams/.  Requires the Graphviz `dot` binary.

Install Graphviz (needed once):
    Fedora/RHEL:    sudo dnf install graphviz
    Ubuntu/Debian:  sudo apt install graphviz
    macOS:          brew install graphviz
    Windows:        choco install graphviz

Usage:
    python scripts/dev/generate_diagrams.py
"""

import shutil
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Preflight: verify graphviz dot binary is available
# ---------------------------------------------------------------------------

def _require_graphviz() -> None:
    if shutil.which("dot"):
        return
    print(
        "ERROR: Graphviz 'dot' binary not found.\n"
        "Install it first, then re-run this script:\n"
        "  Fedora/RHEL:   sudo dnf install graphviz\n"
        "  Ubuntu/Debian: sudo apt install graphviz\n"
        "  macOS:         brew install graphviz\n"
        "  Windows:       choco install graphviz\n"
    )
    sys.exit(1)


_require_graphviz()

# Deferred imports — only after graphviz check passes
from diagrams import Cluster, Diagram, Edge  # noqa: E402
from diagrams.generic.compute import Rack  # noqa: E402
from diagrams.generic.storage import Storage  # noqa: E402
from diagrams.programming.language import Python  # noqa: E402

OUT = Path("docs/diagrams")
OUT.mkdir(parents=True, exist_ok=True)

GRAPH_ATTR = {"fontsize": "13", "bgcolor": "white", "pad": "0.5"}
NODE_ATTR  = {"fontsize": "11"}


# ---------------------------------------------------------------------------
# 1. System Architecture
# ---------------------------------------------------------------------------

def system_architecture() -> None:
    with Diagram(
        "EnvisionPerdido — System Architecture",
        filename=str(OUT / "system_architecture"),
        show=False,
        direction="TB",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
    ):
        with Cluster("Input Sources"):
            web_scraper = Python("Web Scrapers\nPerdido Chamber\nWren Haven\nMulti-source")
            ics_parser  = Python("ICS Parser\n(perdido_chamber_\nscraper.py)")

        with Cluster("Data Collection & Normalization"):
            data_loader = Python("DataCollection\n& Normalizer\n(event_normalizer.py)")
            events_df   = Storage("events.csv\ntitle · desc · location\nstart · url")

        with Cluster("Training Path  (offline)"):
            svm_train    = Python("SVM Training\nsvm_train_from_file.py\n(LinearSVC)")
            tfidf_fit    = Python("TF-IDF Vectorizer\nfit & save")

        with Cluster("Model Artifacts  data/artifacts/"):
            model_pkl      = Storage("event_classifier\n_model.pkl")
            vectorizer_pkl = Storage("event_vectorizer\n.pkl")

        with Cluster("Inference  (automated_pipeline.py)"):
            load_model     = Python("Load Model\n& Vectorizer\n(cached)")
            classify       = Python("classify_events()")
            batch_classify = Python("classify_events_batch()\n500 events / batch")

        with Cluster("Output Enrichment"):
            normalizer   = Python("Event Normalizer\n• Tags  • Venue\n• needs_review flag")
            image_assign = Python("Image Assignment\n• Keyword match\n• Score & assign")
            export_node  = Python("Export Events\nCSV / JSON")
            email_node   = Python("Email Summary\n(reviewers)")
            wp_upload    = Python("WordPress Upload\n• Create drafts\n• Set metadata\n• Publish")

        output_store = Storage("output/pipeline/\ncalendar_upload_*.csv\nlogs/")

        with Cluster("Dev Tools  (optional)"):
            dev_tools = Python("profile_inference.py\nvisualize_pipeline.py")

        # ── edges ──────────────────────────────────────────────────────────
        [web_scraper, ics_parser] >> data_loader >> events_df

        events_df >> svm_train
        svm_train >> tfidf_fit
        tfidf_fit >> [model_pkl, vectorizer_pkl]

        events_df >> load_model
        [model_pkl, vectorizer_pkl] >> load_model
        load_model >> [classify, dev_tools]
        classify >> batch_classify >> normalizer

        normalizer >> image_assign >> export_node >> email_node >> wp_upload >> output_store

        # feedback loop
        output_store >> Edge(label="Label corrections", style="dashed", color="gray") >> svm_train


# ---------------------------------------------------------------------------
# 2. Batch Classification Flow
# ---------------------------------------------------------------------------

def batch_classification_flow() -> None:
    with Diagram(
        "Batch Classification Flow",
        filename=str(OUT / "batch_classification"),
        show=False,
        direction="TB",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
    ):
        input_events = Storage("Input Events\n(~1 500 total)")
        batch_fn     = Python("classify_events_batch()\nbatch_size = 500")

        with Cluster("Parallel Batches"):
            b1 = Rack("Batch 1\n500 events")
            b2 = Rack("Batch 2\n500 events")
            b3 = Rack("Batch 3\n500 events")
            b4 = Rack("Batch 4\nremainder")

        with Cluster("Per-Batch Steps"):
            vectorize  = Python("TF-IDF\nVectorize")
            predict    = Python("SVM Predict\n(LinearSVC)")
            conf_score = Python("Confidence Score\nsigmoid(decision_func)")

        merge = Python(
            "Merge Results\n"
            "• is_community_event\n"
            "• confidence  [0,1]\n"
            "• needs_review flag"
        )

        input_events >> batch_fn >> [b1, b2, b3, b4]
        [b1, b2, b3, b4] >> vectorize >> predict >> conf_score >> merge


# ---------------------------------------------------------------------------
# 3. Data Transformation Pipeline
# ---------------------------------------------------------------------------

def data_transformation_pipeline() -> None:
    with Diagram(
        "Data Transformation Pipeline",
        filename=str(OUT / "data_transformation"),
        show=False,
        direction="TB",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
    ):
        raw = Storage(
            "Raw Event\n"
            "title · description\n"
            "location · start · url"
        )

        feat_eng = Python(
            "Feature Engineering\n"
            "build_features()\n"
            "title + desc + location + category"
        )

        vectorize = Python(
            "TF-IDF Vectorization\n"
            "ngram_range=(1,2)\n"
            "min_df=2  max_df=0.9\n"
            "sublinear_tf=True"
        )

        feat_matrix = Rack(
            "Sparse Feature Matrix\n"
            "shape: (N, ~1 000)\n"
            "type: csr_matrix\n"
            "density: ~1–2 %"
        )

        svm = Python(
            "SVM Classification\n"
            "LinearSVC\n"
            "class_weight='balanced'\n"
            "max_iter=1000"
        )

        conf = Python(
            "Confidence Score\n"
            "sigmoid(decision_function)\n"
            "→ [0, 1]"
        )

        enriched = Storage(
            "Enriched Event\n"
            "is_community · confidence\n"
            "needs_review  (< 0.75)\n"
            "tags · venue · image_url"
        )

        raw >> feat_eng >> vectorize >> feat_matrix >> svm >> conf >> enriched


# ---------------------------------------------------------------------------
# 4. Package / File Dependency Graph
# ---------------------------------------------------------------------------

def file_dependency_graph() -> None:
    with Diagram(
        "Script Package Dependencies",
        filename=str(OUT / "file_dependencies"),
        show=False,
        direction="LR",
        graph_attr=GRAPH_ATTR,
        node_attr=NODE_ATTR,
    ):
        with Cluster("scripts/ (entry-points / wrappers)"):
            pipeline_entry  = Python("automated_pipeline.py")
            uploader_entry  = Python("wordpress_uploader.py")
            health_entry    = Python("health_check.py")
            scraper_entry   = Python("multi_calendar_scraper.py")

        with Cluster("scripts/pipeline/"):
            auto_pipeline = Python("automated_pipeline")
            wp_uploader   = Python("wordpress_uploader")
            health_check  = Python("health_check")
            regen_desc    = Python("regenerate_descriptions")

        with Cluster("scripts/ml/"):
            svm_train  = Python("svm_train_from_file")
            svm_tag    = Python("svm_tag_events")
            auto_label = Python("auto_label_and_train")
            model_view = Python("modelViewer")

        with Cluster("scripts/tooling/"):
            env_loader    = Python("env_loader")
            logger_mod    = Python("logger")
            normalizer    = Python("event_normalizer")
            venue_reg     = Python("venue_registry")
            tag_tax       = Python("tag_taxonomy")

        with Cluster("scripts/scrapers/"):
            perdido_sc = Python("perdido_chamber_scraper")
            wren_sc    = Python("wren_haven_scraper")
            multi_sc   = Python("multi_calendar_scraper")

        with Cluster("data/"):
            artifacts = Storage("artifacts/\nmodel.pkl\nvectorizer.pkl")
            raw_data  = Storage("raw/  labeled/\n*.csv  *.json")
            cache     = Storage("cache/")

        # wrapper → implementation
        pipeline_entry  >> auto_pipeline
        uploader_entry  >> wp_uploader
        health_entry    >> health_check
        scraper_entry   >> multi_sc

        # pipeline uses tooling
        auto_pipeline >> [env_loader, logger_mod, normalizer, venue_reg, tag_tax]
        auto_pipeline >> artifacts
        wp_uploader   >> [env_loader, cache]

        # ml uses artifacts
        svm_train  >> artifacts
        auto_label >> [svm_train, raw_data]
        svm_tag    >> artifacts

        # scrapers produce data
        [perdido_sc, wren_sc, multi_sc] >> raw_data


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    steps = [
        ("system_architecture",      system_architecture),
        ("batch_classification",     batch_classification_flow),
        ("data_transformation",      data_transformation_pipeline),
        ("file_dependencies",        file_dependency_graph),
    ]

    print(f"Generating {len(steps)} diagrams → {OUT}/\n")
    for name, fn in steps:
        fn()
        print(f"  ✓  {name}.png")

    print("\nDone.")
