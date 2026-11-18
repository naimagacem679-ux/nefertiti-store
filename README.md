# Néfertiti — مشروع المتجر المستقل (Cloudflare)

**المرحلة الحالية: 1 من 4.** لم يُعدَّل المتجر. `public/index.html` نسخة مطابقة للأصل بايتاً ببايت.

## ما في المجلد
```
public/index.html            المتجر كما هو (لم يتغير)
db/schema.sql                مخطط قاعدة D1
db/seed.sql                  بياناتك الحالية جاهزة للاستيراد (مولَّدة، لا تُعدَّل يدوياً)
db/source/                   النسخة الاحتياطية الأصلية + SHA256SUMS.txt (للقراءة فقط)
seed-images/                 صور المتجر المستخرجة (الشعار، الغلاف، دوائر التواصل، QR) لرفعها إلى R2
scripts/                     make_seed.py · verify_seed.py · test_order_flow.py · check_original_untouched.sh · upload_seed_images.sh
docs/                        حالات الطلب · حماية الإدارة · الحدود والتكاليف · قائمة الشروط
functions/                   فارغ الآن (المرحلة 2)
wrangler.toml                ربط D1 وR2 بالأسماء فقط، بلا أسرار
```

## افحصي المرحلة 1 على أي حاسوب (يحتاج Python 3 فقط)
```
python3 -I scripts/verify_seed.py            # يحمّل المخطط والبيانات ويقارنها بالأصل
python3 -I scripts/test_order_flow.py        # يختبر قواعد الطلبات والمخزون
bash scripts/check_original_untouched.sh     # يتحقق من SHA256 ومن تطابق الصفحة مع الأصل
```

## ما بعد المرحلة 1
2. دوال الخادم وCloudflare Access · 3. ربط الواجهة بالدوال بأقل تعديل ممكن · 4. النشر التجريبي واختبار الهاتف ثم الإطلاق.
