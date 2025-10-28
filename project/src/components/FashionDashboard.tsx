import React, { useState, useEffect } from "react";
import { Shirt, Loader2, AlertCircle, Palette, Package } from "lucide-react";

interface FashionItem {
  item_name: string;
  color_name: string;
  materials: string;
  color_hex: string;
  designer: string;
  collection: string;
  season: string;
  original_image_name: string;
  image_id: string;
  timestamp: string;
}

interface GroupedData {
  [key: string]: FashionItem[];
}

interface Dataset {
  id: string;
  name: string;
  description: string;
  designer: string;
  season: string;
  collection: string;
  s3Bucket: string;
  apiEndpoint: string;
}

interface FashionDashboardProps {
  dataset: Dataset;
  filteredData?: FashionItem[];
}

export function FashionDashboard({ dataset, filteredData }: FashionDashboardProps) {
  const [data, setData] = useState<GroupedData>({});
  const [rawData, setRawData] = useState<FashionItem[]>([]);
  const [folderMap, setFolderMap] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ✅ Fetch S3 folder map + DynamoDB items
  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);

        // 1️⃣ Fetch folder mapping (brand → season → folder)
        const folderRes = await fetch(
          "https://ucyq5e10ok.execute-api.eu-west-2.amazonaws.com/default/listS3Folders"
        );
        const folderJson = await folderRes.json();

        const parsedFolderMap =
          typeof folderJson.body === "string" ? JSON.parse(folderJson.body) : folderJson;

        setFolderMap(parsedFolderMap);

        // 2️⃣ Fetch fashion data
        const res = await fetch(dataset.apiEndpoint);
        if (!res.ok) throw new Error(`HTTP error: ${res.status}`);
        const result = await res.json();

        const normalize = (s: string) => s?.toLowerCase().replace(/[-_]/g, " ").trim();

        // Filter data (by designer + season)
        const dataToUse =
          filteredData ||
          result.filter((item: FashionItem) => {
            const itemBrand = normalize(item.designer);
            const datasetBrand = normalize(dataset.designer);
            const itemSeason = normalize(item.season);
            const datasetSeason = normalize(dataset.season);
            return itemBrand === datasetBrand && itemSeason === datasetSeason;
          });

        setRawData(dataToUse);

        // Group by original image name
        const grouped = dataToUse.reduce((acc: GroupedData, item) => {
          const name = item.original_image_name;
          acc[name] = acc[name] || [];
          acc[name].push(item);
          return acc;
        }, {});
        setData(grouped);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Error fetching data");
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [dataset, filteredData]);

  // ✅ Build correct S3 folder path
  function getFolder(brand: string, season: string) {
    const normalize = (s: string) => s?.toLowerCase().replace(/[-_]/g, " ").trim();
    const brandKey = normalize(brand);
    const seasonKey = normalize(season);

    const mappedFolder =
      folderMap[brandKey]?.[seasonKey] ||
      `${brandKey.replace(/\s+/g, "-")}-ready-to-wear-${seasonKey.replace(/\s+/g, "-")}-paris`;

    return mappedFolder;
  }

  // ✅ Helpers
  const getUniqueItems = (items: FashionItem[], key: keyof FashionItem) =>
    [...new Set(items.map((i) => i[key]))]
      .filter(Boolean)
      .map((v) => (v as string).charAt(0).toUpperCase() + (v as string).slice(1));

  const getUniqueColors = (items: FashionItem[]) => {
    const unique = new Map<string, string>();
    items.forEach((i) => {
      if (i.color_name && !unique.has(i.color_name)) unique.set(i.color_name, i.color_hex);
    });
    return Array.from(unique.entries()).map(([name, hex]) => ({
      name: name.charAt(0).toUpperCase() + name.slice(1),
      hex,
    }));
  };

  // ✅ States
  if (loading)
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4 text-green-600" />
          <p className="text-gray-600">Loading fashion analysis...</p>
        </div>
      </div>
    );

  if (error)
    return (
      <div className="flex items-center justify-center h-96 text-center">
        <AlertCircle className="w-8 h-8 mx-auto mb-2 text-red-500" />
        <p className="text-red-600">{error}</p>
      </div>
    );

  // ✅ Render
  return (
    <div className="space-y-8">
      <h3 className="text-2xl font-semibold text-gray-800 text-center mb-8">
        Fashion Analysis Overview
      </h3>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <SummaryCard
          icon={<Palette className="w-8 h-8 text-green-600" />}
          label="Total Colors"
          value={new Set(rawData.map((i) => i.color_name)).size}
        />
        <SummaryCard
          icon={<Shirt className="w-8 h-8 text-green-600" />}
          label="Clothing Items"
          value={new Set(rawData.map((i) => i.item_name)).size}
        />
        <SummaryCard
          icon={<Package className="w-8 h-8 text-green-600" />}
          label="Materials"
          value={new Set(rawData.map((i) => i.materials)).size}
        />
      </div>

      {/* Image Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        {Object.entries(data).map(([imageName, items]) => (
          <FashionCard
            key={items[0].image_id || imageName}
            imageName={imageName}
            items={items}
            s3Bucket="runwayimages"
            getFolder={getFolder}
            getUniqueItems={getUniqueItems}
            getUniqueColors={getUniqueColors}
          />
        ))}
      </div>
    </div>
  );
}

// ✅ SummaryCard
function SummaryCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 flex items-center">
      <div className="mr-3">{icon}</div>
      <div>
        <p className="text-sm text-gray-600">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}

// ✅ FashionCard
function FashionCard({
  imageName,
  items,
  s3Bucket,
  getFolder,
  getUniqueItems,
  getUniqueColors,
}: {
  imageName: string;
  items: FashionItem[];
  s3Bucket: string;
  getFolder: (brand: string, season: string) => string;
  getUniqueItems: (items: FashionItem[], key: keyof FashionItem) => string[];
  getUniqueColors: (items: FashionItem[]) => { name: string; hex: string }[];
}) {
  const [imageError, setImageError] = useState(false);
  const item = items[0];
  const folder = getFolder(item.designer, item.season);
  const imageUrl = `https://${s3Bucket}.s3.eu-west-2.amazonaws.com/${folder}/${item.original_image_name}`;

  const clothing = getUniqueItems(items, "item_name");
  const colors = getUniqueColors(items);
  const materials = getUniqueItems(items, "materials");

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-300">
      {/* Image */}
      <div className="aspect-square bg-gray-100 relative">
        {!imageError ? (
          <img
            src={imageUrl}
            alt={imageName}
            className="w-full h-full object-cover"
            loading="lazy"
            onError={() => setImageError(true)}
          />
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            <Shirt className="w-10 h-10" />
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <div className="flex justify-between items-center mb-3">
          <h4 className="font-semibold text-gray-900">{item.designer || "Unknown"}</h4>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            {item.season}
          </span>
        </div>

        <DetailSection title="Clothing Items" values={clothing} />
        <ColorSection colors={colors} />
        <DetailSection title="Materials" values={materials} color="green" />
      </div>
    </div>
  );
}

// ✅ DetailSection + ColorSection
function DetailSection({
  title,
  values,
  color,
}: {
  title: string;
  values: string[];
  color?: "green";
}) {
  const baseColor =
    color === "green" ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-700";
  return (
    <div className="mb-3">
      <h5 className="font-medium text-gray-700 mb-2">{title}</h5>
      <div className="flex flex-wrap gap-1">
        {values.map((v) => (
          <span
            key={v}
            className={`${baseColor} px-2 py-1 rounded-full text-xs`}
          >
            {v}
          </span>
        ))}
      </div>
    </div>
  );
}

function ColorSection({ colors }: { colors: { name: string; hex: string }[] }) {
  return (
    <div className="mb-3">
      <h5 className="font-medium text-gray-700 mb-2">Colors</h5>
      <div className="flex flex-wrap gap-2">
        {colors.map((c) => (
          <div key={c.name} className="flex items-center gap-2">
            <div
              className="w-4 h-4 rounded-full border border-gray-300"
              style={{ backgroundColor: c.hex }}
              title={`${c.name} (${c.hex})`}
            />
            <span className="text-xs text-gray-600">{c.name}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
