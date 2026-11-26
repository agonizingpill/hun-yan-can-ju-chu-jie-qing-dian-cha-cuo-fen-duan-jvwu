from domain.manifest import banquet_tables,cases

FIXTURES=(
    (banquet_tables,[
        {'code':'MH-A08','hall':'玉兰厅','party':'甄林婚宴','seats':10,'course':'冷盘','runner':'何师傅'},
        {'code':'MH-A10','hall':'玉兰厅','party':'甄林婚宴','seats':8,'course':'席间加盘','runner':'吴师傅'},
        {'code':'MH-C01','hall':'迎宾侧厅','party':'敬茶小席','seats':6,'course':'甜羹','runner':'顾师傅'},
    ]),
    (cases,[
        {'code':'CASE-R08','dish':'金边盖盘','capacity':12,'lid_tag':'LID-R08'},
        {'code':'CASE-R10','dish':'银边盖盘','capacity':10,'lid_tag':'LID-R10'},
        {'code':'CASE-C01','dish':'甜羹碗','capacity':8,'lid_tag':'LID-C01'},
        {'code':'CASE-C02','dish':'甜羹小碟','capacity':8,'lid_tag':'LID-C02'},
    ]),
)
