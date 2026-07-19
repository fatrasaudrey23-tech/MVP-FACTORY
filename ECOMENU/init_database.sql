-- 🚀 SCRIPT D'INITIALISATION AUTOMATIQUE SECURED
-- Généré et corrigé par l'Agent DevOps de la MVP Factory

-- Table : Informations sur les utilisateurs et leurs préférences
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    budget_max NUMERIC(10, 2),
    taille_foyer INTEGER,
    gestion_restes BOOLEAN DEFAULT FALSE,
    type_boite_lunch TEXT,
    profil_boite_lunch TEXT
);

ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Table : Enseignes sélectionnées par les utilisateurs
CREATE TABLE IF NOT EXISTS public.enseigne_selection (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    enseigne TEXT
);

ALTER TABLE public.enseigne_selection ENABLE ROW LEVEL SECURITY;

-- Table : Données promotionnelles extraites des circulaires
CREATE TABLE IF NOT EXISTS public.promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    enseigne TEXT,
    nom_produit TEXT,
    prix_promo NUMERIC(10, 2),
    poids_volume TEXT,
    unite_mesure TEXT,
    categorie_alimentaire TEXT
);

ALTER TABLE public.promotions ENABLE ROW LEVEL SECURITY;

-- Table : Tags standardisés pour les produits
CREATE TABLE IF NOT EXISTS public.produit_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nom_produit TEXT,
    tag_standard TEXT
);

ALTER TABLE public.produit_tags ENABLE ROW LEVEL SECURITY;

-- Table : Menus hebdomadaires générés pour les utilisateurs
CREATE TABLE IF NOT EXISTS public.menus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    menu_data VARCHAR(255),
    date_generation TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE public.menus ENABLE ROW LEVEL SECURITY;

