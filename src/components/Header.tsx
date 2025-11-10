import { NavLink } from "@/components/NavLink";

export function Header() {
  return (
    <header
      className="sticky top-0 z-50 backdrop-blur-xl border-b"
      style={{
        background: "rgba(252, 255, 247, 0.8)",
        borderColor: "rgba(155, 182, 144, 0.2)",
        boxShadow: "0 1px 3px rgba(155, 182, 144, 0.1)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <NavLink to="/" className="flex items-center gap-3 group">
          <img
            src="cropped_image (2).png" // 👈 replace with your actual logo path (e.g. "/assets/logo.svg")
            alt=".fi logo"
            className="w-8 h-8 object-contain transition-transform group-hover:scale-110"
          />
          <span className="font-semibold text-lg bg-gradient-to-r from-[#9bb690] to-[#f8d8d8] bg-clip-text text-transparent">
    
          </span>
        </NavLink>

        {/* Nav Links */}
        <nav className="flex items-center gap-8">
          <NavLink
            to="/"
            end
            className="text-sm font-light text-gray-700 hover:text-[#9bb690] transition-colors relative"
            activeClassName="text-[#9bb690] after:absolute after:bottom-[-4px] after:left-0 after:w-full after:h-0.5 after:bg-gradient-to-r after:from-[#9bb690] after:to-[#f8d8d8]"
          >
            Data
          </NavLink>
        </nav>
      </div>
    </header>
  );
}
