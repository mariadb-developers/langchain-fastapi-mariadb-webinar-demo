import logging
import os
import random
from typing import Dict, List, Optional

import httpx
from nicegui import ui

# API configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
DEMO_API_KEY = os.getenv("DEMO_API_KEY", "demo-key-123")

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(levelname)s:     %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Product categories for the outdoor gear store
CATEGORIES = ["Camping Gear", "Apparel", "Footwear", "Winter Sports"]


class OutdoorGearStore:
    def __init__(self):
        self.current_query = ""
        self.current_category = "Camping Gear"

    async def search_products(
        self, query: str, category: str, k: int = 10
    ) -> Optional[List[Dict]]:
        """Search products using the FastAPI backend"""
        try:
            headers = {"X-API-Key": DEMO_API_KEY}
            params = {"search_query": query, "category": category, "k": k}

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE_URL}/search-products",
                    headers=headers,
                    params=params,
                    timeout=30.0,
                )

            if response.status_code == 200:
                data = response.json()
                return data.get("results", [])
            else:
                log.error(f"API error: {response.status_code} - {response.text}")
                ui.notify(f"Search failed: {response.status_code}", type="negative")
                return None

        except httpx.TimeoutException:
            log.error("Search request timed out")
            ui.notify("Search timed out. Please try again.", type="negative")
            return None
        except Exception as e:
            log.error(f"Search error: {e}")
            ui.notify("An error occurred during search", type="negative")
            return None

    def create_product_card(self, product: Dict) -> None:
        """Create a product card UI component"""
        # Random outdoor gear icons
        outdoor_icons = [
            "🏔️",
            "⛺",
            "🎒",
            "🥾",
            "🧗",
            "🏕️",
            "🔦",
            "🧭",
            "⛷️",
            "🏂",
            "🚵",
            "🏃",
            "🎿",
            "🥇",
            "⚡",
            "🌲",
        ]
        icon = random.choice(outdoor_icons)

        with ui.card().classes(
            "w-full h-full shadow-lg hover:shadow-xl transition-shadow duration-300"
        ):
            # Product image placeholder
            with ui.card_section().classes("p-0 w-full"):
                ui.html(
                    f'<div class="w-full h-48 bg-gradient-to-br from-gray-200 to-gray-300 flex items-center justify-center"><span class="text-gray-500 text-9xl">{icon}</span></div>'
                ).style("width: 100%; display: block;")

            with ui.card_section().classes("pb-2"):
                ui.label(product.get("name", "Unknown Product")).classes(
                    "text-h5 font-bold text-gray-800"
                )

            with ui.card_section().classes("py-2 flex-grow"):
                description = product.get("description", "No description available")
                # Truncate long descriptions
                if len(description) > 150:
                    description = description[:150] + "..."
                ui.label(description).classes("text-body2 text-gray-600 line-clamp-3")

            with ui.card_section().classes("pt-2 pb-4"):
                # Price placeholder (since we don't have price data)
                ui.label("Price on request").classes(
                    "text-lg font-bold text-primary mb-2"
                )

            with ui.card_actions().classes("px-4 pb-4 pt-0"):
                with ui.row().classes("w-full gap-2"):
                    ui.button("View Details", icon="visibility").classes(
                        "flex-grow"
                    ).on("click", lambda _, p=product: self.show_product_details(p))
                    ui.button(
                        "Add to Cart", icon="shopping_cart", color="primary"
                    ).classes("flex-grow").on(
                        "click", lambda _: ui.notify("Added to cart!", type="positive")
                    )

    def show_product_details(self, product: Dict) -> None:
        """Show detailed product information in a dialog"""
        with ui.dialog() as dialog, ui.card():
            ui.label(product.get("name", "Unknown Product")).classes(
                "text-h5 font-bold mb-4"
            )
            ui.separator()

            with ui.column().classes("gap-4 mt-4"):
                ui.label("Description:").classes("text-subtitle1 font-bold")
                ui.label(
                    product.get("description", "No description available")
                ).classes("text-body1")

                if product.get("id"):
                    ui.label(f"Product ID: {product['id']}").classes(
                        "text-caption text-grey-6"
                    )

            with ui.row().classes("justify-end mt-4"):
                ui.button("Close", on_click=dialog.close)

        dialog.open()

    async def perform_search(
        self, query_input, category_select, results_container
    ) -> None:
        """Perform search and update results"""
        query = query_input.value.strip()
        category = category_select.value

        if not query:
            ui.notify("Please enter a search query", type="warning")
            return

        # Show loading state
        results_container.clear()
        with results_container:
            ui.spinner(size="lg")
            ui.label("Searching products...").classes("text-center mt-4")

        self.current_search = query
        self.current_category = category

        # Perform search
        results = await self.search_products(query, category)

        # Update results
        results_container.clear()

        if results is None:
            with results_container:
                ui.label("Search failed. Please try again.").classes(
                    "text-center text-red-500"
                )
            return

        if not results:
            with results_container:
                ui.label("No products found matching your search.").classes(
                    "text-center text-grey-600"
                )
            return

        self.search_results = results

        with results_container:
            # Results header
            with ui.row().classes("justify-between items-center mb-6"):
                ui.label(f"Found {len(results)} products").classes("text-2xl font-bold")
                with ui.row().classes("gap-2"):
                    ui.button("Grid View", icon="grid_view", color="primary")
                    ui.button("List View", icon="view_list")

            # Product grid
            with ui.element("div").classes(
                "grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
            ):
                for product in results:
                    self.create_product_card(product)

    def create_search_interface(self) -> None:
        """Create the main search interface"""
        # Add global CSS to remove default margins and padding
        ui.add_head_html(
            """
        <style>
            html, body {
                margin: 0 !important;
                padding: 0 !important;
                overflow-x: hidden;
            }
            .q-page, .q-page-container {
                padding: 0 !important;
                margin: 0 !important;
            }
            .q-header {
                margin-bottom: 0 !important;
            }
            .q-layout {
                margin: 0 !important;
                padding: 0 !important;
            }
            /* Fix the nicegui-content padding that causes the bottom gap */
            .nicegui-content {
                padding: 0 !important;
            }
        </style>
        """
        )

        # Header with navigation - fixed height to prevent text cut-off
        with ui.header().classes("items-center justify-between px-6 py-4").style(
            "min-height: 80px; max-height: 80px; overflow: hidden;"
        ):
            with ui.row().classes("items-center gap-4 no-wrap"):
                ui.label("🏔️ Outdoor Gear Store").classes(
                    "text-h4 font-bold whitespace-nowrap"
                )
                # Navigation menu
                with ui.row().classes("gap-4 ml-8 no-wrap"):
                    ui.button("Home").classes(
                        "text-white bg-transparent hover:bg-white hover:bg-opacity-20"
                    )
                    ui.button("Categories").classes(
                        "text-white bg-transparent hover:bg-white hover:bg-opacity-20"
                    )
                    ui.button("About").classes(
                        "text-white bg-transparent hover:bg-white hover:bg-opacity-20"
                    )
                    ui.button("Contact").classes(
                        "text-white bg-transparent hover:bg-white hover:bg-opacity-20"
                    )

            with ui.row().classes("items-center gap-4 no-wrap"):
                # Cart icon
                ui.button(icon="shopping_cart").classes(
                    "text-white bg-transparent hover:bg-white hover:bg-opacity-20"
                )
                ui.button(icon="account_circle").classes(
                    "text-white bg-transparent hover:bg-white hover:bg-opacity-20"
                )

                # Powered by section
                with ui.row().classes("items-center gap-2 no-wrap ml-4"):
                    ui.label("Powered by").classes("text-subtitle2")
                    ui.html(
                        '<img src="https://mariadb.com/wp-content/uploads/2019/11/mariadb-logo_white-transparent.png" alt="MariaDB" style="height: 24px; width: auto; vertical-align: middle;">'
                    ).classes("flex-shrink-0")

        # Hero section with background image - full width and properly styled
        with ui.element("div").classes(
            "relative bg-cover bg-center bg-no-repeat text-white"
        ).style(
            """
            background-image: url('https://media.istockphoto.com/id/1443409611/fi/valokuva/mies-kivell%C3%A4-kukkulalla-ja-kauniit-vuoret-sumussa-v%C3%A4rikk%C3%A4%C3%A4ss%C3%A4-auringonlaskussa-syksyll%C3%A4.jpg?s=1024x1024&w=is&k=20&c=i8qQFZFQNwtFXegb723C0WhOd2aY_Ak8cFuXU2ykwVw=');
            width: 100vw;
            margin: 0;
            margin-left: calc(-50vw + 50%);
            margin-top: 80px;
            padding: 4rem 0;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
        """
        ):
            # Dark overlay for better text readability
            with ui.element("div").classes("absolute inset-0 bg-black bg-opacity-50"):
                pass
            with ui.column().classes("relative z-10 px-6 max-w-4xl").style(
                "text-align: center; margin: 0 auto;"
            ):
                ui.label("Find Your Perfect Outdoor Gear").classes(
                    "text-3xl md:text-4xl lg:text-5xl font-bold mb-6 text-white drop-shadow-lg"
                ).style("text-align: center; word-wrap: break-word;")
                ui.label(
                    "Discover high-quality equipment for all your outdoor adventures"
                ).classes(
                    "text-lg md:text-xl mb-8 text-white opacity-95 drop-shadow-md"
                ).style(
                    "text-align: center;"
                )

                # Search components in hero banner
                with ui.row().classes(
                    "w-full gap-4 items-end justify-center max-w-2xl mx-auto"
                ):
                    category_select2 = (
                        ui.select(
                            options=CATEGORIES, value="Camping Gear", label="Category"
                        )
                        .classes("w-48")
                        .props("outlined dense")
                        .style(
                            "background-color: rgba(255,255,255,0.95); border-radius: 8px;"
                        )
                    )

                    query_input2 = (
                        ui.input(
                            label="What are you looking for? (type and press ENTER)",
                            placeholder="e.g., waterproof hiking boots, camping tent, climbing gear...",
                        )
                        .classes("flex-grow min-w-80")
                        .props("outlined dense")
                        .style(
                            "background-color: rgba(255,255,255,0.95); border-radius: 8px;"
                        )
                    )

                    # Add search icon to the input field
                    with query_input2.add_slot("prepend"):
                        ui.icon("search").classes("text-gray-500")

        # Main content - consistent width (smaller for better centering)
        with ui.column().classes("w-full max-w-4xl mx-auto p-6 gap-6"):
            # Results section
            results_container = ui.column().classes("w-full")

            # Add ENTER key handler for search (must be after results_container is defined)
            query_input2.on(
                "keydown.enter",
                lambda: self.perform_search(
                    query_input2, category_select2, results_container
                ),
            )

            # Search section
            with ui.card().classes("shadow-lg w-full"):
                with ui.card_section().classes("p-8 text-center w-full").style(
                    "width: 100%;"
                ):
                    ui.icon("hiking", size="4rem").classes("text-primary mb-4")
                    ui.label("Welcome to Our Outdoor Gear Store").classes(
                        "text-2xl font-bold mb-6"
                    )
                    ui.label(
                        "Browse our popular categories or search above to find the perfect gear for your next adventure!"
                    ).classes("text-base mb-4 text-gray-600")

                    # Popular Categories subtitle
                    ui.label("Popular Categories").classes(
                        "text-lg font-semibold mb-3 mt-6"
                    )
                    with ui.row().classes("w-full gap-3 flex-wrap justify-center"):
                        for category in [
                            "Camping Gear",
                            "Apparel",
                            "Footwear",
                            "Winter Sports",
                        ]:
                            ui.chip(
                                category, color="primary", text_color="white"
                            ).classes("cursor-pointer text-lg px-6 py-3")

    def run_app(self) -> None:
        """Run the NiceGUI application"""
        # Set up the UI with MariaDB brand colors
        ui.colors(
            primary="#003545",  # MariaDB dark blue
            secondary="#BA834A",  # MariaDB gold/bronze
            accent="#F5F5F5",  # Light gray for accents
            dark="#003545",
            positive="#4CAF50",
            negative="#F44336",
            info="#2196F3",
            warning="#FF9800",
        )

        # Create the interface
        self.create_search_interface()

        # Footer - full width with no borders or margins
        with ui.element("footer").classes("bg-gray-800 text-white p-8 w-full").style(
            "margin: 0; width: 100vw; margin-left: calc(-50vw + 50%);"
        ):
            with ui.column().classes("w-full max-w-7xl mx-auto"):
                with ui.row().classes("justify-between gap-8"):
                    with ui.column().classes("gap-2"):
                        ui.label("Outdoor Gear Store").classes("text-xl font-bold mb-2")
                        ui.label("Your trusted partner for outdoor adventures")
                        ui.label("📧 info@outdoorgear.com")
                        ui.label("📞 1-800-OUTDOOR")

                    with ui.column().classes("gap-2"):
                        ui.label("Categories").classes("text-lg font-semibold mb-2")
                        ui.label("Hiking & Trekking")
                        ui.label("Camping Equipment")
                        ui.label("Climbing Gear")
                        ui.label("Water Sports")

                    with ui.column().classes("gap-2"):
                        ui.label("Customer Service").classes(
                            "text-lg font-semibold mb-2"
                        )
                        ui.label("Contact Us")
                        ui.label("Shipping Info")
                        ui.label("Returns")
                        ui.label("Size Guide")

                ui.separator().classes("my-6")
                with ui.row().classes("justify-between items-center"):
                    ui.label("© 2024 Outdoor Gear Store. All rights reserved.")
                    with ui.row().classes("items-center gap-2"):
                        ui.label("Powered by").classes("text-sm")
                        ui.html(
                            '<img src="https://mariadb.com/wp-content/uploads/2019/11/mariadb-logo_white-transparent.png" alt="MariaDB" style="height: 16px; width: auto;">'
                        )

        # Configure and run
        ui.run(
            title="Outdoor Gear Store",
            favicon="🏔️",
            host="0.0.0.0",
            port=8080,
            show=True,
        )


def main():
    """Main entry point"""
    log.info("Starting NiceGUI frontend...")
    store = OutdoorGearStore()
    store.run_app()


if __name__ in {"__main__", "__mp_main__"}:
    main()
