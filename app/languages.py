"""Language names and the short sample sentence used for voice previews.
Native speakers should review the rarer ones before you ship."""
LANGUAGES = {
    "en": ("English", "Hello, this is a quick preview of how this voice sounds."),
    "es": ("Spanish", "Hola, esta es una breve muestra de cómo suena esta voz."),
    "fr": ("French", "Bonjour, voici un court aperçu de la sonorité de cette voix."),
    "it": ("Italian", "Ciao, questa è una breve anteprima di come suona questa voce."),
    "pt": ("Portuguese", "Olá, esta é uma breve amostra de como esta voz soa."),
    "hi": ("Hindi", "नमस्ते, यह एक छोटा सा नमूना है कि यह आवाज़ कैसी सुनाई देती है।"),
    "ar": ("Arabic", "مرحباً، هذه معاينة قصيرة لتسمع كيف يبدو هذا الصوت."),
    "de": ("German", "Hallo, das ist eine kurze Hörprobe, wie diese Stimme klingt."),
    "nl": ("Dutch", "Hallo, dit is een korte voorbeeldopname van hoe deze stem klinkt."),
    "tr": ("Turkish", "Merhaba, bu sesin nasıl duyulduğuna dair kısa bir örnektir."),
    "ru": ("Russian", "Здравствуйте, это короткий пример того, как звучит этот голос."),
    "ja": ("Japanese", "こんにちは、これはこの声がどのように聞こえるかの短いサンプルです。"),
    "zh": ("Chinese", "你好，这是一段简短的示例，让你听听这个声音的效果。"),
    "ko": ("Korean", "안녕하세요, 이 목소리가 어떻게 들리는지 보여 드리는 짧은 샘플입니다."),
    "pl": ("Polish", "Cześć, to jest krótka próbka tego, jak brzmi ten głos."),
    "sv": ("Swedish", "Hej, det här är ett kort smakprov på hur den här rösten låter."),
    "da": ("Danish", "Hej, det her er en kort prøve på, hvordan denne stemme lyder."),
    "fi": ("Finnish", "Hei, tämä on lyhyt esimerkki siitä, miltä tämä ääni kuulostaa."),
    "el": ("Greek", "Γεια σας, αυτό είναι ένα σύντομο δείγμα του πώς ακούγεται αυτή η φωνή."),
    "he": ("Hebrew", "שלום, זו דוגמה קצרה לאופן שבו הקול הזה נשמע."),
    "no": ("Norwegian", "Hei, dette er en kort prøve på hvordan denne stemmen høres ut."),
    "ms": ("Malay", "Helo, ini ialah contoh ringkas bagaimana suara ini kedengaran."),
    "sw": ("Swahili", "Habari, huu ni mfano mfupi wa jinsi sauti hii inavyosikika."),
}

# Languages each engine can speak (verified against the model documentation).
KOKORO_LANGS = ["en", "es", "fr", "hi", "it", "pt"]
CHATTERBOX_LANGS = ["ar", "da", "de", "el", "en", "es", "fi", "fr", "he", "hi", "it", "ja",
                    "ko", "ms", "nl", "no", "pl", "pt", "ru", "sv", "sw", "tr", "zh"]


def language_list(codes):
    return [{"code": c, "name": LANGUAGES[c][0]} for c in codes]


def preview_text(code):
    return LANGUAGES.get(code, LANGUAGES["en"])[1]
