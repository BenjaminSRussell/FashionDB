#!/bin/bash
# Master script to run all analysis tools

set -e  # Exit on error

echo "=========================================="
echo "FashionDB Complete Analysis Suite"
echo "=========================================="
echo ""

# Create reports directory
mkdir -p reports

echo "[1/4] Analyzing query effectiveness..."
python3 tools/analyze_queries.py
echo "✓ Query analysis complete"
echo ""

echo "[2/4] Running performance benchmarks..."
python3 tools/benchmark.py
echo "✓ Benchmarks complete"
echo ""

echo "[3/4] Optimizing query set..."
python3 tools/optimize_queries.py
echo "✓ Query optimization complete"
echo ""

echo "[4/4] Generating summary report..."

# Create summary report
cat > reports/SUMMARY.txt << 'EOF'
========================================
FashionDB Analysis Summary
========================================

Reports generated:
1. query_effectiveness.txt - Which queries work best
2. benchmark_report.txt - Performance metrics
3. query_optimization.txt - Optimized query set

Next steps:
1. Review the reports above
2. Read IMPLEMENTATION_ROADMAP.md
3. Choose your implementation path:
   - Option A: Full migration (recommended)
   - Option B: Incremental improvements
   - Option C: Continue as-is

Quick commands:
- Migrate to SQLite: python3 tools/migrate_to_sqlite.py
- Re-run analysis: ./run_analysis.sh
- Start scraping with optimized queries: (update scraper config first)

For detailed strategy, see:
- ANALYSIS_AND_STRATEGY.md
- IMPLEMENTATION_ROADMAP.md
- tools/README.md
EOF

cat reports/SUMMARY.txt

echo ""
echo "=========================================="
echo "Analysis complete! 🎉"
echo "=========================================="
echo ""
echo "All reports saved to: reports/"
echo "Next: Review reports and see IMPLEMENTATION_ROADMAP.md"
echo ""
