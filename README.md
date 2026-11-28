# Ball Escape Auto Shorts

يصنع فيديو Short عمودي (1080×1920) لكرة تكسر حلقات حلزونية، بصوت مولّد، وينشره على يوتيوب.

- كل تشغيل مختلف: كرة واحدة أو سباق كرتين، عدد الحلقات، الوقت، الألوان، وشكل الحلزون.
- النشر التلقائي: 1:30 ظهراً و8:30 مساءً بتوقيت العراق (GitHub ممكن يتأخر بالمواعيد).
- بدون مفاتيح يوتيوب: يصنع الفيديو فقط ويحفظه 7 أيام ضمن التشغيل.

## الإعداد من الموبايل (مرة واحدة)

1. بموقع console.cloud.google.com اختر مشروعك وفعّل **YouTube Data API v3**.
2. بصفحة OAuth consent خلّي حالة التطبيق **In production** (بوضع Testing ينتهي التوكن بعد 7 أيام).
3. من Credentials أنشئ **OAuth client ID** نوعه **Web application**، وأضف Redirect URI:
   `https://developers.google.com/oauthplayground`
4. افتح developers.google.com/oauthplayground ثم ⚙️ وفعّل **Use your own OAuth credentials** وضع الـID والـSecret.
5. بخانة النطاق اكتب `https://www.googleapis.com/auth/youtube.upload` ثم **Authorize APIs**،
   واختر **قناة الألعاب** (وليس قناة أخرى).
6. اضغط **Exchange authorization code for tokens** وانسخ **Refresh token**.
7. بالمستودع: Settings → Secrets and variables → Actions، وأضف:
   `YOUTUBE_CLIENT_ID` و `YOUTUBE_CLIENT_SECRET` و `YOUTUBE_REFRESH_TOKEN`

**لا تضع المفاتيح داخل أي ملف ولا ترسلها بمحادثة.**

## التجربة
Actions ← Ball Escape - Generate and Publish ← Run workflow، واختر `private` لأول مرة.

> إذا كان مشروع Google جديداً وغير مدقَّق، قد يقفل يوتيوب الفيديوهات المرفوعة عبر الـAPI على «خاص»
> حتى لو اخترت عام. وقتها يلزم تقديم طلب تدقيق API إلى يوتيوب.

## الملفات
- `src/simulator.py` — المحاكاة والصوت والعنوان
- `src/publish_youtube.py` — الرفع على يوتيوب
- `src/publish_metricool.py` — قديم، لم يعد مستخدماً بسير العمل
