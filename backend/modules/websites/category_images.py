"""
Category-specific image library — يضمن أن كل قالب داخل فئة معينة يستخدم صور
من نفس الموضوع (مطعم في فئة المطاعم، سباكة في فئة السباكة، إلخ).

Each category has 8-10 curated Unsplash photos covering different angles/moods.
The renderer picks a deterministic image per archetype using hash → ensures
each of the 25 templates within one category shows a *different* photo
without becoming random/inconsistent across reloads.
"""
from typing import List, Dict
import hashlib

# 8 صور احترافية متنوعة لكل فئة — كلها من نفس الموضوع لكن بزوايا/أمزجة مختلفة
CATEGORY_IMAGES: Dict[str, List[str]] = {
    "restaurant": [
        "https://images.unsplash.com/photo-1414235077428-338989a2e8c0?w=1600&q=70",   # plated dish overhead
        "https://images.unsplash.com/photo-1559339352-11d035aa65de?w=1600&q=70",      # restaurant interior warm
        "https://images.unsplash.com/photo-1424847651672-bf20a4b0982b?w=1600&q=70",   # fine dining
        "https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1600&q=70",   # pasta plate
        "https://images.unsplash.com/photo-1555396273-367ea4eb4db5?w=1600&q=70",      # chef plating
        "https://images.unsplash.com/photo-1466637574441-749b8f19452f?w=1600&q=70",   # ingredients flatlay
        "https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=1600&q=70",      # burger gourmet
        "https://images.unsplash.com/photo-1544025162-d76694265947?w=1600&q=70",      # steak medium
    ],
    "coffee": [
        "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085?w=1600&q=70",   # latte art top
        "https://images.unsplash.com/photo-1453614512568-c4024d13c247?w=1600&q=70",   # coffee shop interior
        "https://images.unsplash.com/photo-1442550528053-c431ecb55509?w=1600&q=70",   # barista pouring
        "https://images.unsplash.com/photo-1521017432531-fbd92d768814?w=1600&q=70",   # espresso shot
        "https://images.unsplash.com/photo-1511920170033-f8396924c348?w=1600&q=70",   # cappuccino with beans
        "https://images.unsplash.com/photo-1497935586351-b67a49e012bf?w=1600&q=70",   # cafe pastries
        "https://images.unsplash.com/photo-1559925393-8be0ec4767c8?w=1600&q=70",      # cold brew
        "https://images.unsplash.com/photo-1559056199-641a0ac8b55e?w=1600&q=70",      # coffee beans macro
    ],
    "store": [
        "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1600&q=70",   # boutique store
        "https://images.unsplash.com/photo-1567401893414-76b7b1e5a7a5?w=1600&q=70",   # clothing store interior
        "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=1600&q=70",      # display window
        "https://images.unsplash.com/photo-1483985988355-763728e1935b?w=1600&q=70",   # shopping bags
        "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?w=1600&q=70",   # fashion rack
        "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=1600&q=70",   # apparel hangers
        "https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1600&q=70",   # ecommerce flatlay
        "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?w=1600&q=70",      # store shelves
    ],
    "barber": [
        "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?w=1600&q=70",   # barber pole shop
        "https://images.unsplash.com/photo-1599351431202-1e0f0137899a?w=1600&q=70",   # man getting shave
        "https://images.unsplash.com/photo-1521590832167-7bcbfaa6381f?w=1600&q=70",   # barber chair vintage
        "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?w=1600&q=70",   # haircut close-up
        "https://images.unsplash.com/photo-1585747860715-2ba37e788b70?w=1600&q=70",   # hipster beard
        "https://images.unsplash.com/photo-1587909209111-5097ee578ec3?w=1600&q=70",   # tools flat lay
        "https://images.unsplash.com/photo-1622287162716-f311baa1a2b8?w=1600&q=70",   # barber working
        "https://images.unsplash.com/photo-1593702288056-7927c8d96b6c?w=1600&q=70",   # straight razor
    ],
    "salon_women": [
        "https://images.unsplash.com/photo-1560066984-138dadb4c035?w=1600&q=70",      # salon interior pink
        "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?w=1600&q=70",   # hair styling
        "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=1600&q=70",   # makeup eye
        "https://images.unsplash.com/photo-1457972729786-0411a3b2b626?w=1600&q=70",   # blow dry
        "https://images.unsplash.com/photo-1595476108010-b4d1f102b1b1?w=1600&q=70",   # nail art
        "https://images.unsplash.com/photo-1580618672591-eb180b1a973f?w=1600&q=70",   # spa massage
        "https://images.unsplash.com/photo-1633681926022-84c23e8cb2d6?w=1600&q=70",   # salon equipment
        "https://images.unsplash.com/photo-1610992015732-2449b76344bc?w=1600&q=70",   # eyebrows microblading
    ],
    "pets": [
        "https://images.unsplash.com/photo-1543466835-00a7907e9de1?w=1600&q=70",      # golden retriever
        "https://images.unsplash.com/photo-1574158622682-e40e69881006?w=1600&q=70",   # cat eyes close
        "https://images.unsplash.com/photo-1601758228041-f3b2795255f1?w=1600&q=70",   # puppy white
        "https://images.unsplash.com/photo-1583337130417-3346a1be7dee?w=1600&q=70",   # dog grooming
        "https://images.unsplash.com/photo-1450778869180-41d0601e046e?w=1600&q=70",   # cat playing
        "https://images.unsplash.com/photo-1561948955-570b270e7c36?w=1600&q=70",      # cat orange tabby
        "https://images.unsplash.com/photo-1444212477490-ca407925329e?w=1600&q=70",   # dog hike
        "https://images.unsplash.com/photo-1535930891776-0c2dfb7fda1a?w=1600&q=70",   # vet exam
    ],
    "clinic": [
        "https://images.unsplash.com/photo-1538108149393-fbbd81895907?w=1600&q=70",   # doctor stethoscope
        "https://images.unsplash.com/photo-1576091160550-2173dba999ef?w=1600&q=70",   # medical team
        "https://images.unsplash.com/photo-1551601651-2a8555f1a136?w=1600&q=70",      # exam room
        "https://images.unsplash.com/photo-1631815589968-fdb09a223b1e?w=1600&q=70",   # doctor consultation
        "https://images.unsplash.com/photo-1579684385127-1ef15d508118?w=1600&q=70",   # dental
        "https://images.unsplash.com/photo-1559757148-5c350d0d3c56?w=1600&q=70",      # clinic hallway
        "https://images.unsplash.com/photo-1582750433449-648ed127bb54?w=1600&q=70",   # nurse smile
        "https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=1600&q=70",   # medical tech
    ],
    "bakery": [
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?w=1600&q=70",   # croissants
        "https://images.unsplash.com/photo-1486427944299-d1955d23e34d?w=1600&q=70",   # sourdough
        "https://images.unsplash.com/photo-1555507036-ab1f4038808a?w=1600&q=70",      # cake decorating
        "https://images.unsplash.com/photo-1568254183919-78a4f43a2877?w=1600&q=70",   # bread loaves
        "https://images.unsplash.com/photo-1517686469429-8bdb88b9f907?w=1600&q=70",   # cupcakes display
        "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?w=1600&q=70",      # macarons
        "https://images.unsplash.com/photo-1608198093002-ad4e005484ec?w=1600&q=70",   # bakery window
        "https://images.unsplash.com/photo-1620980776848-84d57e0fa6ed?w=1600&q=70",   # baker hands
    ],
    "car_wash": [
        "https://images.unsplash.com/photo-1605164599901-db7f68c4b1a4?w=1600&q=70",   # car being washed
        "https://images.unsplash.com/photo-1520340356584-f9917d1eea6f?w=1600&q=70",   # foam soap
        "https://images.unsplash.com/photo-1601362840469-51e4d8d58785?w=1600&q=70",   # detailing wax
        "https://images.unsplash.com/photo-1558981359-219d6364c9c8?w=1600&q=70",      # wheel rim shine
        "https://images.unsplash.com/photo-1607860108855-64acf2078ed9?w=1600&q=70",   # spraying water
        "https://images.unsplash.com/photo-1532581140115-3e355d1ed1de?w=1600&q=70",   # red car polished
        "https://images.unsplash.com/photo-1493238792000-8113da705763?w=1600&q=70",   # vacuuming interior
        "https://images.unsplash.com/photo-1543467091-5f0406620f8b?w=1600&q=70",      # car drying
    ],
    "sports_club": [
        "https://images.unsplash.com/photo-1571902943202-507ec2618e8f?w=1600&q=70",   # gym dumbbells
        "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=1600&q=70",   # crossfit class
        "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1600&q=70",   # boxing gloves
        "https://images.unsplash.com/photo-1518611012118-696072aa579a?w=1600&q=70",   # running track
        "https://images.unsplash.com/photo-1599058917765-a780eda07a3e?w=1600&q=70",   # weights rack
        "https://images.unsplash.com/photo-1581009146145-b5ef050c2e1e?w=1600&q=70",   # athlete sprint
        "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=1600&q=70",   # basketball hoop
        "https://images.unsplash.com/photo-1574680096145-d05b474e2155?w=1600&q=70",   # gym mirror equipment
    ],
    "library": [
        "https://images.unsplash.com/photo-1507842217343-583bb7270b66?w=1600&q=70",   # bookshelves rows
        "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?w=1600&q=70",   # library hall classical
        "https://images.unsplash.com/photo-1568667256549-094345857637?w=1600&q=70",   # books stack
        "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?w=1600&q=70",   # study corner
        "https://images.unsplash.com/photo-1495446815901-a7297e633e8d?w=1600&q=70",   # open book reading
        "https://images.unsplash.com/photo-1457369804613-52c61a468e7d?w=1600&q=70",   # ladder library
        "https://images.unsplash.com/photo-1588580000645-4562a6d2c839?w=1600&q=70",   # notebooks pencils
        "https://images.unsplash.com/photo-1506880018603-83d5b814b5a6?w=1600&q=70",   # vintage books open
    ],
    "art_gallery": [
        "https://images.unsplash.com/photo-1577720580479-7d839d829c73?w=1600&q=70",   # museum gallery
        "https://images.unsplash.com/photo-1531058020387-3be344556be6?w=1600&q=70",   # paintings hung
        "https://images.unsplash.com/photo-1547826039-bfc35e0f1ea8?w=1600&q=70",      # sculpture marble
        "https://images.unsplash.com/photo-1499781350541-7783f6c6a0c8?w=1600&q=70",   # canvas painting
        "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?w=1600&q=70",   # contemporary art
        "https://images.unsplash.com/photo-1548136540-a4ed3535b2f7?w=1600&q=70",      # gallery visitor
        "https://images.unsplash.com/photo-1605429523419-d828abe6b9e9?w=1600&q=70",   # abstract canvas
        "https://images.unsplash.com/photo-1518998053901-5348d3961a04?w=1600&q=70",   # museum architecture
    ],
    "maintenance": [
        "https://images.unsplash.com/photo-1581094271901-8022df4466f9?w=1600&q=70",   # technician computer
        "https://images.unsplash.com/photo-1530124566582-a618bc2615dc?w=1600&q=70",   # tools workshop
        "https://images.unsplash.com/photo-1581092580497-e0d23cbdf1dc?w=1600&q=70",   # repair circuit
        "https://images.unsplash.com/photo-1563770557593-978789a4a728?w=1600&q=70",   # ac repair
        "https://images.unsplash.com/photo-1504917595217-d4dc5ebe6122?w=1600&q=70",   # electrician
        "https://images.unsplash.com/photo-1622314920104-04bdadbd935e?w=1600&q=70",   # screwdriver close
        "https://images.unsplash.com/photo-1595079676714-d97e2c39c0c2?w=1600&q=70",   # tech work bench
        "https://images.unsplash.com/photo-1589939705384-5185137a7f0f?w=1600&q=70",   # plumbing tools
    ],
    "jewelry": [
        "https://images.unsplash.com/photo-1611652022417-a551c4e6e0a7?w=1600&q=70",   # gold ring close
        "https://images.unsplash.com/photo-1601121141461-9d6647bca1ed?w=1600&q=70",   # diamond necklace
        "https://images.unsplash.com/photo-1605100804763-247f67b3557e?w=1600&q=70",   # earrings pearls
        "https://images.unsplash.com/photo-1599643477877-530eb83abc8e?w=1600&q=70",   # bracelet gold
        "https://images.unsplash.com/photo-1543294001-f7cd5d7fb516?w=1600&q=70",      # gold chains
        "https://images.unsplash.com/photo-1602173574767-37ac01994b2a?w=1600&q=70",   # luxury watch
        "https://images.unsplash.com/photo-1584302179602-e4c3d3fd629d?w=1600&q=70",   # diamond ring solitaire
        "https://images.unsplash.com/photo-1515562141207-7a88fb7ce338?w=1600&q=70",   # jewelry display
    ],
    "gym": [
        "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?w=1600&q=70",   # boxing
        "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=1600&q=70",   # treadmills row
        "https://images.unsplash.com/photo-1593079831268-3381b0db4a77?w=1600&q=70",   # fitness woman pushup
        "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=1600&q=70",   # group class
        "https://images.unsplash.com/photo-1605296867304-46d5465a13f1?w=1600&q=70",   # kettle bell swing
        "https://images.unsplash.com/photo-1549060279-7e168fcee0c2?w=1600&q=70",      # bodybuilder back
        "https://images.unsplash.com/photo-1576678927484-cc907957088c?w=1600&q=70",   # spin bike
        "https://images.unsplash.com/photo-1540497077202-7c8a3999166f?w=1600&q=70",   # squat barbell
    ],
    "academy": [
        "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?w=1600&q=70",   # classroom modern
        "https://images.unsplash.com/photo-1523240795612-9a054b0db644?w=1600&q=70",   # student laptop
        "https://images.unsplash.com/photo-1427504494785-3a9ca7044f45?w=1600&q=70",   # graduation cap
        "https://images.unsplash.com/photo-1606761568499-6d2451b23c66?w=1600&q=70",   # online learning
        "https://images.unsplash.com/photo-1509062522246-3755977927d7?w=1600&q=70",   # whiteboard
        "https://images.unsplash.com/photo-1497486751825-1233686d5d80?w=1600&q=70",   # books learning
        "https://images.unsplash.com/photo-1571260899304-425eee4c7efc?w=1600&q=70",   # student writing
        "https://images.unsplash.com/photo-1543269865-cbf427effbad?w=1600&q=70",      # group study
    ],
    "plumbing": [
        "https://images.unsplash.com/photo-1542013936693-884638332954?w=1600&q=70",   # plumber wrench
        "https://images.unsplash.com/photo-1585704032915-c3400ca199e7?w=1600&q=70",   # pipes
        "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=1600&q=70",      # bathroom faucet
        "https://images.unsplash.com/photo-1581092160562-40aa08e78837?w=1600&q=70",   # plumber hands
        "https://images.unsplash.com/photo-1574708541748-de8e1f10cd56?w=1600&q=70",   # under sink
        "https://images.unsplash.com/photo-1615996001375-c7ef13294187?w=1600&q=70",   # tools blue
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=1600&q=70",      # water drop sink
        "https://images.unsplash.com/photo-1565128939600-0fb2f3c46e07?w=1600&q=70",   # pipe fitting
    ],
    "electrical": [
        "https://images.unsplash.com/photo-1620625515032-6ed0c1790c75?w=1600&q=70",   # electrician at panel
        "https://images.unsplash.com/photo-1595079676714-d97e2c39c0c2?w=1600&q=70",   # tools electric
        "https://images.unsplash.com/photo-1565608438257-fac3c27beb36?w=1600&q=70",   # cables wires
        "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4?w=1600&q=70",   # light bulb concept
        "https://images.unsplash.com/photo-1581092335397-9583eb92d232?w=1600&q=70",   # control panel
        "https://images.unsplash.com/photo-1591370874773-6702e8f12fd8?w=1600&q=70",   # outlet socket
        "https://images.unsplash.com/photo-1545259741-2ea3ebf61fa3?w=1600&q=70",      # solar panels
        "https://images.unsplash.com/photo-1627053671833-4b48f95cad3a?w=1600&q=70",   # technician electric
    ],
    "company": [
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1600&q=70",   # office bright
        "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1600&q=70",      # team meeting
        "https://images.unsplash.com/photo-1556761175-5973dc0f32e7?w=1600&q=70",      # business handshake
        "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?w=1600&q=70",   # corporate building
        "https://images.unsplash.com/photo-1573164713988-8665fc963095?w=1600&q=70",   # business woman
        "https://images.unsplash.com/photo-1521737711867-e3b97375f902?w=1600&q=70",   # team brainstorming
        "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40?w=1600&q=70",   # data dashboard
        "https://images.unsplash.com/photo-1551434678-e076c223a692?w=1600&q=70",      # office collaboration
    ],
    "portfolio": [
        "https://images.unsplash.com/photo-1542744173-8e7e53415bb0?w=1600&q=70",
        "https://images.unsplash.com/photo-1499951360447-b19be8fe80f5?w=1600&q=70",   # creative workspace
        "https://images.unsplash.com/photo-1512486130939-2c4f79935e4f?w=1600&q=70",   # design tools
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1600&q=70",   # code on screen
        "https://images.unsplash.com/photo-1561070791-2526d30994b8?w=1600&q=70",      # creative ideation
        "https://images.unsplash.com/photo-1572177812156-58036aae439c?w=1600&q=70",   # photographer
        "https://images.unsplash.com/photo-1519337265831-281ec6cc8514?w=1600&q=70",   # color palette art
        "https://images.unsplash.com/photo-1581291518857-4e27b48ff24e?w=1600&q=70",   # lighting setup
    ],
    "saas": [
        "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1600&q=70",      # dashboard analytics
        "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1600&q=70",   # code dark
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1600&q=70",   # circuit board
        "https://images.unsplash.com/photo-1488590528505-98d2b5aba04b?w=1600&q=70",   # laptop neon
        "https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1600&q=70",      # programming text
        "https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1600&q=70",   # office screen
        "https://images.unsplash.com/photo-1633409361618-c73427e4e206?w=1600&q=70",   # chart growth
        "https://images.unsplash.com/photo-1639762681485-074b7f938ba0?w=1600&q=70",   # cloud abstract
    ],
    "cosmetics": [
        "https://images.unsplash.com/photo-1487412947147-5cebf100ffc2?w=1600&q=70",   # makeup eye
        "https://images.unsplash.com/photo-1522335789203-aaa50abf7090?w=1600&q=70",   # lipstick pink
        "https://images.unsplash.com/photo-1596462502278-27bfdc403348?w=1600&q=70",   # cosmetics flatlay
        "https://images.unsplash.com/photo-1615397349754-cfa2066a298e?w=1600&q=70",   # perfume bottles
        "https://images.unsplash.com/photo-1631214540242-4d9be3a9bd76?w=1600&q=70",   # makeup brushes
        "https://images.unsplash.com/photo-1571781926291-c477ebfd024b?w=1600&q=70",   # eyeshadow palette
        "https://images.unsplash.com/photo-1612817288484-6f916006741a?w=1600&q=70",   # skincare products
        "https://images.unsplash.com/photo-1596704017254-9b121068fb31?w=1600&q=70",   # foundation cream
    ],
    "automotive": [
        "https://images.unsplash.com/photo-1494976388531-d1058494cdd8?w=1600&q=70",   # car red
        "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=1600&q=70",   # mercedes
        "https://images.unsplash.com/photo-1580273916550-e323be2ae537?w=1600&q=70",   # bmw
        "https://images.unsplash.com/photo-1502877338535-766e1452684a?w=1600&q=70",   # suv white
        "https://images.unsplash.com/photo-1542362567-b07e54358753?w=1600&q=70",      # ferrari yellow
        "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?w=1600&q=70",   # vintage car
        "https://images.unsplash.com/photo-1606664515524-ed2f786a0bd6?w=1600&q=70",   # showroom
        "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?w=1600&q=70",   # luxury sedan
    ],
    "realestate": [
        "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=1600&q=70",      # luxury house
        "https://images.unsplash.com/photo-1486325212027-8081e485255e?w=1600&q=70",   # modern building
        "https://images.unsplash.com/photo-1613490493576-7fde63acd811?w=1600&q=70",   # mansion luxury
        "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?w=1600&q=70",   # apartment view
        "https://images.unsplash.com/photo-1564013799919-ab600027ffc6?w=1600&q=70",   # modern villa
        "https://images.unsplash.com/photo-1567496898669-ee935f5f647a?w=1600&q=70",   # interior living room
        "https://images.unsplash.com/photo-1582407947304-fd86f028f716?w=1600&q=70",   # luxury bedroom
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1600&q=70",   # city skyline
    ],
    "blank": [
        "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1600&q=70",
        "https://images.unsplash.com/photo-1497032628192-86f99bcd76bc?w=1600&q=70",
        "https://images.unsplash.com/photo-1486312338219-ce68d2c6f44d?w=1600&q=70",
        "https://images.unsplash.com/photo-1531403009284-440f080d1e12?w=1600&q=70",
        "https://images.unsplash.com/photo-1517048676732-d65bc937f952?w=1600&q=70",
        "https://images.unsplash.com/photo-1497366811353-6870744d04b2?w=1600&q=70",
        "https://images.unsplash.com/photo-1579403124614-197f69d8187b?w=1600&q=70",
        "https://images.unsplash.com/photo-1542435503-956c469947f6?w=1600&q=70",
    ],
}


def _stable_index(seed: str, mod: int) -> int:
    """Deterministic index from a string seed (so the same archetype always picks the same image)."""
    if not seed or mod <= 0:
        return 0
    h = hashlib.md5(seed.encode("utf-8")).digest()
    return h[0] % mod


def get_category_images(category_id: str) -> List[str]:
    """Return curated image list for a category (or blank fallback)."""
    return CATEGORY_IMAGES.get(category_id) or CATEGORY_IMAGES["blank"]


def pick_images_for_archetype(category_id: str, archetype_id: str, count: int = 4) -> List[str]:
    """
    Pick `count` distinct images for a given archetype within a category.
    Different archetypes inside the same category get DIFFERENT image rotations
    (deterministic — same archetype always picks same images).
    """
    lib = get_category_images(category_id)
    n = len(lib)
    start = _stable_index(f"{category_id}:{archetype_id}", n)
    return [lib[(start + i) % n] for i in range(count)]
