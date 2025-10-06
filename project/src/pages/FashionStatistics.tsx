import React, { useEffect, useState } from "react";
import { Palette, Package, Layers, ChevronDown } from "lucide-react";

// Helper: fetch and parse NDJSON
async function fetchNDJSON(url: string) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}`);
  const text = await res.text();
  return text
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line));
}

export function FashionStatistics() {
  const [colors, setColors] = useState<any[]>([]);
  const [items, setItems] = useState<any[]>([]);
  const [materials, setMaterials] = useState<any[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<string>("");
  const [selectedSeason, setSelectedSeason] = useState<string>("");

  // Load datasets
  useEffect(() => {
    Promise.all([
      fetchNDJSON(
        "https://fashion-trend-forecast-data.s3.eu-west-2.amazonaws.com/processed/colors.json"
      ),
      fetchNDJSON(
        "https://fashion-trend-forecast-data.s3.eu-west-2.amazonaws.com/processed/items.json"
      ),
      fetchNDJSON(
        "https://fashion-trend-forecast-data.s3.eu-west-2.amazonaws.com/processed/materials.json"
      ),
    ])
      .then(([c, i, m]) => {
        setColors(c);
        setItems(i);
        setMaterials(m);
      })
      .catch((err) => console.error("Error loading data:", err));
  }, []);

  // Utility: get top N sorted by frequency
  const getTopN = (data: any[], n: number) =>
    [...data]
      .sort((a, b) => b.frequency - a.frequency)
      .slice(0, n)
      .map((d, idx) => ({ 
        rank: idx + 1, 
        ...d,
        color_name: d.color_name ? d.color_name.charAt(0).toUpperCase() + d.color_name.slice(1) : d.color_name,
        item_name: d.item_name ? d.item_name.charAt(0).toUpperCase() + d.item_name.slice(1) : d.item_name,
        materials: d.materials ? d.materials.charAt(0).toUpperCase() + d.materials.slice(1) : d.materials
      }));

  // ---- Global Filters ----
  const applyFilters = (data: any[]) =>
    data.filter((d) => {
      const brandMatch = selectedBrand ? d.designer === selectedBrand : true;
      const seasonMatch = selectedSeason ? d.season === selectedSeason : true;
      return brandMatch && seasonMatch;
    });

  // Unique brands
  const brands = Array.from(
    new Set([...colors, ...items, ...materials].map((d) => d.designer))
  ).filter(Boolean);

  const normalizeSeason = (s: string) => {
    if (!s) return s;
    const lower = s.toLowerCase().replace(/[-_]/g, " ").replace(/\s+/g, " ");
    if (lower.includes("fall") && lower.includes("winter") && lower.includes("2024"))
      return "Fall-Winter 2024";
    if (lower.includes("spring") && lower.includes("summer") && lower.includes("2024"))
      return "Spring-Summer 2024";
    return s;
  };

  const availableSeasons = Array.from(
    new Set(
      [...colors, ...items, ...materials]
        .filter((d) => (selectedBrand ? d.designer === selectedBrand : true))
        .map((d) => normalizeSeason(d.season))
    )
  );

  // Apply filters to each dataset
  const topColors = getTopN(applyFilters(colors), 10);
  const topItems = getTopN(applyFilters(items), 10);
  const topMaterials = getTopN(applyFilters(materials), 10);

  const topColor = topColors[0];
  const topItem = topItems[0];
  const topMaterial = topMaterials[0];

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-3xl font-bold text-gray-900 mb-2">
          Fashion Statistics
        </h2>
        <p className="text-gray-600">
          AI-powered trend prediction and emerging fashion insights.
        </p>
      </div>

      {/* Global Filter Bar */}
      <div className="flex gap-4 mb-6">
        {/* Brand filter */}
        <div className="relative">
          <select
            className="appearance-none border rounded-md px-4 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={selectedBrand}
            onChange={(e) => {
              setSelectedBrand(e.target.value);
              setSelectedSeason(""); // reset season if brand changes
            }}
          >
            <option value="">All Brands</option>
            {brands.map((b, idx) => (
              <option key={idx} value={b}>
                {b}
              </option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 absolute right-2 top-3 text-gray-500 pointer-events-none" />
        </div>

        {/* Season filter */}
        <div className="relative">
          <select
            className="appearance-none border rounded-md px-4 py-2 pr-8 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={selectedSeason}
            onChange={(e) => setSelectedSeason(e.target.value)}
          >
            <option value="">All Seasons</option>
            {availableSeasons.map((s, idx) => (
              <option key={idx} value={s}>
                {s}
              </option>
            ))}
          </select>
          <ChevronDown className="w-4 h-4 absolute right-2 top-3 text-gray-500 pointer-events-none" />
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 mb-10">
        <div className="bg-white shadow-md rounded-lg p-6 flex items-center">
          <Palette className="w-8 h-8 text-purple-600 mr-4" />
          <div>
            <p className="text-sm text-gray-500">Top Color</p>
            <p className="text-lg font-semibold text-gray-900">
              {topColor ? topColor.color_name : "—"}
            </p>
            <p className="text-xs text-gray-500">
              {topColor ? `${topColor.designer}, ${topColor.season}` : ""}
            </p>
          </div>
        </div>

        <div className="bg-white shadow-md rounded-lg p-6 flex items-center">
          <Package className="w-8 h-8 text-purple-600 mr-4" />
          <div>
            <p className="text-sm text-gray-500">Top Item</p>
            <p className="text-lg font-semibold text-gray-900">
              {topItem ? topItem.item_name : "—"}
            </p>
            <p className="text-xs text-gray-500">
              {topItem ? `${topItem.designer}, ${topItem.season}` : ""}
            </p>
          </div>
        </div>

        <div className="bg-white shadow-md rounded-lg p-6 flex items-center">
          <Layers className="w-8 h-8 text-purple-600 mr-4" />
          <div>
            <p className="text-sm text-gray-500">Top Material</p>
            <p className="text-lg font-semibold text-gray-900">
              {topMaterial ? topMaterial.materials : "—"}
            </p>
            <p className="text-xs text-gray-500">
              {topMaterial ? `${topMaterial.designer}, ${topMaterial.season}` : ""}
            </p>
          </div>
        </div>
      </div>

      {/* Top Colors Table */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-4">
          <Palette className="w-6 h-6 text-purple-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">
            Top 10 Colors
          </h3>
        </div>
        {topColors.length === 0 ? (
          <p className="text-gray-500">No data for selected filters</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b">
              <tr>
                <th className="px-2 py-2">Rank</th>
                <th className="px-2 py-2">Color</th>
                <th className="px-2 py-2">Brand</th>
                <th className="px-2 py-2">Season</th>
                <th className="px-2 py-2">Frequency</th>
              </tr>
            </thead>
            <tbody>
              {topColors.map((row) => (
                <tr key={row.rank} className="border-b">
                  <td className="px-2 py-2">{row.rank}</td>
                  <td className="px-2 py-2">{row.color_name}</td>
                  <td className="px-2 py-2">{row.designer}</td>
                  <td className="px-2 py-2">{row.season}</td>
                  <td className="px-2 py-2">{row.frequency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Top Items Table */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-4">
          <Package className="w-6 h-6 text-purple-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">Top 10 Items</h3>
        </div>
        {topItems.length === 0 ? (
          <p className="text-gray-500">No data for selected filters</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b">
              <tr>
                <th className="px-2 py-2">Rank</th>
                <th className="px-2 py-2">Item</th>
                <th className="px-2 py-2">Brand</th>
                <th className="px-2 py-2">Season</th>
                <th className="px-2 py-2">Frequency</th>
              </tr>
            </thead>
            <tbody>
              {topItems.map((row) => (
                <tr key={row.rank} className="border-b">
                  <td className="px-2 py-2">{row.rank}</td>
                  <td className="px-2 py-2">{row.item_name}</td>
                  <td className="px-2 py-2">{row.designer}</td>
                  <td className="px-2 py-2">{row.season}</td>
                  <td className="px-2 py-2">{row.frequency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Top Materials Table */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center mb-4">
          <Layers className="w-6 h-6 text-purple-600 mr-3" />
          <h3 className="text-xl font-semibold text-gray-900">
            Top 10 Materials
          </h3>
        </div>
        {topMaterials.length === 0 ? (
          <p className="text-gray-500">No data for selected filters</p>
        ) : (
          <table className="min-w-full text-left text-sm">
            <thead className="border-b">
              <tr>
                <th className="px-2 py-2">Rank</th>
                <th className="px-2 py-2">Material</th>
                <th className="px-2 py-2">Brand</th>
                <th className="px-2 py-2">Season</th>
                <th className="px-2 py-2">Frequency</th>
              </tr>
            </thead>
            <tbody>
              {topMaterials.map((row) => (
                <tr key={row.rank} className="border-b">
                  <td className="px-2 py-2">{row.rank}</td>
                  <td className="px-2 py-2">{row.materials}</td>
                  <td className="px-2 py-2">{row.designer}</td>
                  <td className="px-2 py-2">{row.season}</td>
                  <td className="px-2 py-2">{row.frequency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
