import json, collections, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f, object_pairs_hook=collections.OrderedDict)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')

# Step 1: Add missing-but-used keys to en.json
en = load_json('frontend/src/i18n/translations/en.json')

# These are used in JSX but missing from en.json master
en_additions = {
    "advisor.explanationSourceNote": "All factors above are real inputs to the recommendation engine — not post-hoc justifications.",
    "arrivalIntel.arrivalsDisclaimer": "⚠️ Arrival volume data is from a demo dataset; live government mandi arrival feeds are not yet available.",
    "arrivalIntel.demoDisclaimer": "🟡 Demo data — this is not a real-time government mandi feed. Live arrival data will appear here when available.",
    "arrivalIntel.forecastDisclaimer": "⚠️ Demo forecast — based on simulated mandi data, not real government data. Use as a methodology illustration only.",
    "arrivalIntel.recommendationExplanation": "Based on net returns, storage cost, and market signals, this is the strongest selling window available.",
    "dashboard.loading": "Loading...",
    "dashboard.market": "Market",
    "dashboard.price": "Price",
    "opportunity.addProduce": "Add Produce",
    "sellingJourney.crop": "Crop",
    "sellingJourney.market": "Market",
    "buyerDemands.paymentTerms.cashOnDelivery": "Cash on delivery",
    "buyerDemands.paymentTerms.neftWithin3Days": "NEFT within 3 days",
    "buyerDemands.paymentTerms.advance50BalanceOnDelivery": "50% advance, balance on delivery",
    "buyerDemands.paymentTerms.fullPaymentOnDelivery": "Full payment on delivery",
    "buyerDemands.paymentTerms.fullPaymentWithin7Days": "Full payment within 7 days",
}

added_to_en = 0
for k, v in en_additions.items():
    if k not in en:
        en[k] = v
        added_to_en += 1

save_json('frontend/src/i18n/translations/en.json', en)
print(f"en.json: added {added_to_en} keys → {len(en)} total")

# Step 2: Propagate to all locales
# For each locale, add these keys with proper translations
locale_additions = {
    "hi": {
        "advisor.explanationSourceNote": "ऊपर के सभी कारक recommendation engine के वास्तविक इनपुट हैं — ये बाद में जोड़े गए कारण नहीं हैं।",
        "arrivalIntel.arrivalsDisclaimer": "⚠️ आवक डेटा डेमो है; वास्तविक सरकारी मंडी आवक फीड अभी उपलब्ध नहीं है।",
        "arrivalIntel.demoDisclaimer": "🟡 डेमो डेटा — यह वास्तविक सरकारी मंडी फीड नहीं है।",
        "arrivalIntel.forecastDisclaimer": "⚠️ डेमो पूर्वानुमान — अनुकरणीय मंडी डेटा पर आधारित, वास्तविक सरकारी डेटा नहीं।",
        "arrivalIntel.recommendationExplanation": "शुद्ध लाभ, भंडारण लागत और बाजार संकेतों के आधार पर यह सबसे मजबूत बिक्री विंडो है।",
        "dashboard.loading": "लोड हो रहा है...",
        "dashboard.market": "बाज़ार",
        "dashboard.price": "भाव",
        "opportunity.addProduce": "उपज जोड़ें",
        "sellingJourney.crop": "फसल",
        "sellingJourney.market": "बाज़ार",
        "buyerDemands.paymentTerms.cashOnDelivery": "डिलीवरी पर नकद",
        "buyerDemands.paymentTerms.neftWithin3Days": "3 दिनों के भीतर NEFT",
        "buyerDemands.paymentTerms.advance50BalanceOnDelivery": "50% अग्रिम, शेष डिलीवरी पर",
        "buyerDemands.paymentTerms.fullPaymentOnDelivery": "डिलीवरी पर पूर्ण भुगतान",
        "buyerDemands.paymentTerms.fullPaymentWithin7Days": "7 दिनों के भीतर पूर्ण भुगतान",
    },
    "mr": {
        "advisor.explanationSourceNote": "वरील सर्व घटक recommendation engine चे वास्तविक इनपुट आहेत — नंतर जोडलेली कारणे नाहीत।",
        "arrivalIntel.arrivalsDisclaimer": "⚠️ आवक डेटा डेमो आहे; वास्तविक सरकारी मंडी आवक फीड अद्याप उपलब्ध नाही।",
        "arrivalIntel.demoDisclaimer": "🟡 डेमो डेटा — हे वास्तविक सरकारी मंडी फीड नाही।",
        "arrivalIntel.forecastDisclaimer": "⚠️ डेमो अंदाज — अनुकरणीय मंडी डेटावर आधारित, वास्तविक सरकारी डेटा नाही।",
        "arrivalIntel.recommendationExplanation": "निव्वळ परतावा, साठवणूक खर्च आणि बाजार संकेतांवर आधारित हे सर्वात मजबूत विक्री विंडो आहे।",
        "dashboard.loading": "लोड होत आहे...",
        "dashboard.market": "बाजार",
        "dashboard.price": "भाव",
        "opportunity.addProduce": "उत्पादन जोडा",
        "sellingJourney.crop": "पीक",
        "sellingJourney.market": "बाजार",
        "buyerDemands.paymentTerms.cashOnDelivery": "डिलिव्हरीवर रोख",
        "buyerDemands.paymentTerms.neftWithin3Days": "3 दिवसांत NEFT",
        "buyerDemands.paymentTerms.advance50BalanceOnDelivery": "50% आगाऊ, शिल्लक डिलिव्हरीवर",
        "buyerDemands.paymentTerms.fullPaymentOnDelivery": "डिलिव्हरीवर पूर्ण पेमेंट",
        "buyerDemands.paymentTerms.fullPaymentWithin7Days": "7 दिवसांत पूर्ण पेमेंट",
    },
    "bn": {
        "advisor.explanationSourceNote": "উপরের সমস্ত কারণগুলি সুপারিশ ইঞ্জিনের প্রকৃত ইনপুট — পরে যোগ করা ব্যাখ্যা নয়।",
        "arrivalIntel.arrivalsDisclaimer": "⚠️ আগমন ডেটা ডেমো; লাইভ সরকারি মান্ডি আগমন ফিড এখনো পাওয়া যাচ্ছে না।",
        "arrivalIntel.demoDisclaimer": "🟡 ডেমো ডেটা — এটি রিয়েল-টাইম সরকারি মান্ডি ফিড নয়।",
        "arrivalIntel.forecastDisclaimer": "⚠️ ডেমো পূর্বাভাস — সিমুলেটেড মান্ডি ডেটার উপর ভিত্তি করে, প্রকৃত সরকারি ডেটা নয়।",
        "arrivalIntel.recommendationExplanation": "নিট রিটার্ন, স্টোরেজ খরচ এবং বাজার সংকেতের উপর ভিত্তি করে এটি সবচেয়ে শক্তিশালী বিক্রয় উইন্ডো।",
        "dashboard.loading": "লোড হচ্ছে...",
        "dashboard.market": "বাজার",
        "dashboard.price": "দাম",
        "opportunity.addProduce": "পণ্য যোগ করুন",
        "sellingJourney.crop": "ফসল",
        "sellingJourney.market": "বাজার",
        "buyerDemands.paymentTerms.cashOnDelivery": "ডেলিভারিতে নগদ",
        "buyerDemands.paymentTerms.neftWithin3Days": "৩ দিনের মধ্যে NEFT",
        "buyerDemands.paymentTerms.advance50BalanceOnDelivery": "৫০% অগ্রিম, বাকি ডেলিভারিতে",
        "buyerDemands.paymentTerms.fullPaymentOnDelivery": "ডেলিভারিতে সম্পূর্ণ পেমেন্ট",
        "buyerDemands.paymentTerms.fullPaymentWithin7Days": "৭ দিনের মধ্যে সম্পূর্ণ পেমেন্ট",
    },
}

# For all remaining locales, use English fallback for these extra keys
remaining_locales = ['ta','te','gu','kn','as','bho','mai','ml','or','pa','ur']
for loc in remaining_locales:
    locale_additions[loc] = {k: v for k, v in en_additions.items()}

# Apply to all locales
locales = list(locale_additions.keys())
for loc in locales:
    path = f'frontend/src/i18n/translations/{loc}.json'
    data = load_json(path)
    added = 0
    for k, v in locale_additions[loc].items():
        if k not in data:
            data[k] = v
            added += 1
    save_json(path, data)
    print(f"{loc}: +{added} new keys → {len(data)} total")

print("Done.")
