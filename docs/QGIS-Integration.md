# QGIS Attribute Form Configuration

Once you have imported concepts into your lookup table using SkosConnect, the final step is to link your map layer (e.g. `excavation_sites`) to the lookup table. This displays user-friendly dropdown lists in attribute forms.

Here is how to set up the **Value Relation** widget in QGIS:

---

## 🛠️ Step-by-Step Configuration

1. In QGIS, double-click your spatial map layer (e.g. `excavation_sites`) in the Layers Panel.
2. Select the **Attributes Form** tab in the Layer Properties dialog.
3. Select your period attribute column in the fields listing (e.g. `period_uri` or `period_id`).
4. Under **Widget Type** (on the right side), change it from *Text Edit* to **Value Relation**.
5. Configure the widget settings:
   * **Layer:** Select your vocabulary lookup table (`vocab_periods` or `time_periods`).
   * **Key column:** `uri` (or `id` if you are using integer foreign keys). This is the key value saved in the map table.
   * **Value column:** Select the language translation column you want displayed in the dropdown menu (e.g. `pref_eng` or `pref_ger`).
   * **Allow NULL value:** Check this if sites are not required to have a period assigned.
   * **Order by value:** Check this to sort the dropdown list alphabetically.
6. Click **OK** to save changes.

---

## 🚀 The Result
Toggle the map layer into edit mode and add a point. QGIS will display a clean dropdown list showing the human-readable names. In the background, QGIS stores the stable URI/ID reference, ensuring data integrity.
