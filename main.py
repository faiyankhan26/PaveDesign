from fastapi import FastAPI, Form, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel


app = FastAPI()


# ==================================================
# Flexible Pavement - VDF
# ==================================================

def get_vdf(commercial_vehicles):
    """
    Indicative VDF.
    Actual VDF should preferably be obtained
    from axle-load survey data.
    """

    if commercial_vehicles <= 150:
        return 1.7

    elif commercial_vehicles <= 1500:
        return 3.9

    else:
        return 5.0


# ==================================================
# Flexible Pavement - Design Traffic
# ==================================================

def calculate_flexible_design_traffic(
    vehicles,
    growth,
    design_life
):
    """
    Preliminary calculation of cumulative
    standard axles in MSA.
    """

    r = growth / 100

    vdf = get_vdf(vehicles)

    # Two-lane two-way road
    distribution_factor = 0.50

    if r == 0:

        cumulative_axles = (
            365
            * vehicles
            * distribution_factor
            * vdf
            * design_life
        )

    else:

        cumulative_axles = (
            365
            * vehicles
            * distribution_factor
            * vdf
            * (((1 + r) ** design_life - 1) / r)
        )

    msa = cumulative_axles / 1_000_000

    return round(msa, 2)


# ==================================================
# Rigid Pavement - Cumulative Traffic
# ==================================================

def calculate_rigid_cumulative_traffic(
    vehicles,
    growth,
    design_life
):

    r = growth / 100

    if r == 0:

        cumulative = (
            365
            * vehicles
            * design_life
        )

    else:

        cumulative = (
            365
            * vehicles
            * (((1 + r) ** design_life - 1) / r)
        )

    return round(cumulative)


# ==================================================
# Rigid Pavement Design
# ==================================================

def calculate_rigid_pavement_design(
    cbr,
    k_value,
    flexural,
    ec
):
    """
    Preliminary rigid pavement thickness estimate.

    Final structural design requires detailed
    traffic, axle-load and fatigue analysis.
    """

    if cbr < 3:
        slab_thickness = 300

    elif cbr < 5:
        slab_thickness = 290

    elif cbr < 8:
        slab_thickness = 280

    else:
        slab_thickness = 270

    base_thickness = 150

    return slab_thickness, base_thickness


# ==================================================
# Flexible Pavement Design
# ==================================================

def calculate_flexible_pavement_design(
    cbr,
    msa
):
    """
    Preliminary flexible pavement layer estimate.

    Final IRC-based design should use the applicable
    design catalogue/procedure and verified inputs.
    """

    if msa <= 2:
        total_thickness = 450

    elif msa <= 5:
        total_thickness = 500

    elif msa <= 10:
        total_thickness = 550

    elif msa <= 20:
        total_thickness = 600

    else:
        total_thickness = 650

    # Subgrade adjustment

    if cbr < 3:
        total_thickness += 50

    elif cbr >= 8:
        total_thickness -= 25

    # Preliminary layer values

    bituminous_thickness = 100
    granular_base_thickness = 250

    granular_subbase_thickness = (
        total_thickness
        - bituminous_thickness
        - granular_base_thickness
    )

    return (
        total_thickness,
        bituminous_thickness,
        granular_base_thickness,
        granular_subbase_thickness
    )


# ==================================================
# Static Files
# ==================================================

app.mount(
    "/static",
    StaticFiles(directory="FrontEnd"),
    name="static"
)


# ==================================================
# Templates
# ==================================================

templates = Jinja2Templates(
    directory="FrontEnd"
)


# ==================================================
# Pydantic Model
# ==================================================

class PavementInput(BaseModel):

    project_name: str = ""

    pavement_type: str

    commercial_vehicles: int

    growth: float

    design_life: int

    cbr: float

    k_value: float

    grade: str

    flexural: float

    ec: float


# ==================================================
# Home Page
# ==================================================

@app.get("/")
def home(request: Request):

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "calculated": False
        }
    )


# ==================================================
# Pavement Design
# ==================================================

@app.post("/design")
def design(

    request: Request,

    project_name: str = Form(""),

    pavement_type: str = Form(...),

    commercial_vehicles: int = Form(...),

    growth: float = Form(...),

    design_life: int = Form(...),

    cbr: float = Form(...),

    k_value: float = Form(...),

    grade: str = Form(...),

    flexural: float = Form(...),

    ec: float = Form(...)
):

    # --------------------------------------------------
    # Input Validation
    # --------------------------------------------------

    if commercial_vehicles <= 0:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Commercial vehicles must be greater than 0.",
                "calculated": False
            }
        )


    if growth < 0:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Traffic growth rate cannot be negative.",
                "calculated": False
            }
        )


    if design_life <= 0:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Design life must be greater than 0.",
                "calculated": False
            }
        )


    if cbr <= 0:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "CBR must be greater than 0.",
                "calculated": False
            }
        )


    if k_value <= 0:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "K-value must be greater than 0.",
                "calculated": False
            }
        )


    if flexural <= 0:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Flexural strength must be greater than 0.",
                "calculated": False
            }
        )


    if ec <= 0:

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error": "Modulus of elasticity must be greater than 0.",
                "calculated": False
            }
        )


    # --------------------------------------------------
    # Create Pydantic Object
    # --------------------------------------------------

    pavement = PavementInput(

        project_name=project_name,

        pavement_type=pavement_type,

        commercial_vehicles=commercial_vehicles,

        growth=growth,

        design_life=design_life,

        cbr=cbr,

        k_value=k_value,

        grade=grade,

        flexural=flexural,

        ec=ec
    )


    # --------------------------------------------------
    # Default Results
    # --------------------------------------------------

    slab_thickness = 0
    base_thickness = 0

    cumulative_traffic = 0
    design_traffic_msa = 0

    total_thickness = 0
    bituminous_thickness = 0
    granular_base_thickness = 0
    granular_subbase_thickness = 0


    # ==================================================
    # RIGID PAVEMENT
    # ==================================================

    if pavement.pavement_type.lower() == "rigid":

        cumulative_traffic = (
            calculate_rigid_cumulative_traffic(

                pavement.commercial_vehicles,

                pavement.growth,

                pavement.design_life
            )
        )


        slab_thickness, base_thickness = (
            calculate_rigid_pavement_design(

                pavement.cbr,

                pavement.k_value,

                pavement.flexural,

                pavement.ec
            )
        )


    # ==================================================
    # FLEXIBLE PAVEMENT
    # ==================================================

    else:

        design_traffic_msa = (
            calculate_flexible_design_traffic(

                pavement.commercial_vehicles,

                pavement.growth,

                pavement.design_life
            )
        )


        (
            total_thickness,
            bituminous_thickness,
            granular_base_thickness,
            granular_subbase_thickness

        ) = calculate_flexible_pavement_design(

            pavement.cbr,

            design_traffic_msa
        )


    # --------------------------------------------------
    # Send Results to Jinja2
    # --------------------------------------------------

    return templates.TemplateResponse(

        "index.html",

        {

            "request": request,

            "calculated": True,

            "project_name":
                pavement.project_name,

            "pavement_type":
                pavement.pavement_type,

            "commercial_vehicles":
                pavement.commercial_vehicles,

            "growth":
                pavement.growth,

            "design_life":
                pavement.design_life,

            "cbr":
                pavement.cbr,

            "k_value":
                pavement.k_value,

            "grade":
                pavement.grade,

            "flexural":
                pavement.flexural,

            "ec":
                pavement.ec,

            # Rigid
            "slab_thickness":
                slab_thickness,

            "base_thickness":
                base_thickness,

            "cumulative_traffic":
                cumulative_traffic,

            # Flexible
            "design_traffic_msa":
                design_traffic_msa,

            "total_thickness":
                total_thickness,

            "bituminous_thickness":
                bituminous_thickness,

            "granular_base_thickness":
                granular_base_thickness,

            "granular_subbase_thickness":
                granular_subbase_thickness,

            "result_cbr":
                pavement.cbr
        }
    )