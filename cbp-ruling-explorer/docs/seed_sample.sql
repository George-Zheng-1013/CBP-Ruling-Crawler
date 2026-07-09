-- =============================================================================
-- CBP Rulings 种子数据（联调用）
-- =============================================================================
-- 用途：向爬虫项目的 rulings 表注入 17 条真实风格样例，覆盖：
--   * 不同年份 (2019-2024)
--   * 状态 active / revoked
--   * 单 HSCODE 与多 HSCODE（hs_codes 为 JSON 数组文本）
--   * 2 条 parse_failed = 1 并附带 parse_error_msg
--
-- ⚠️ 列名严格对齐 cbp-crawler/storage.py 中 rulings 表的真实定义：
--    ruling_no, subject, description, hs_code, hs_codes, year, detail_url,
--    ruling_date, status, parse_failed, parse_error_msg, is_exported
--    (created_at / updated_at 有默认值，可不写)
--
-- ⚠️ 本应用后端以只读方式连接数据库（mode=ro），因此种子数据必须用
--    **独立的可写连接** 注入，不能直接通过后端接口写入。
--
-- 加载方式（需要写权限，请用 sqlite3 CLI 或另行可写连接）：
--   sqlite3 "D:\HP\OneDrive\Desktop\学校\项目\生产实习\cbp-crawler\data\db\cbp_rulings.db" < docs/seed_sample.sql
--
-- 或使用 Python：
--   import sqlite3, pathlib
--   db = sqlite3.connect(r"D:\HP\OneDrive\Desktop\学校\项目\生产实习\cbp-crawler\data\db\cbp_rulings.db")
--   db.executescript(pathlib.Path("docs/seed_sample.sql").read_text(encoding="utf-8"))
--   db.commit()
-- =============================================================================

DELETE FROM rulings;  -- 便于重复注入时清空旧种子

INSERT INTO rulings
  (ruling_no, subject, description, hs_code, hs_codes, year, detail_url, ruling_date, status, parse_failed, parse_error_msg, is_exported)
VALUES
  ('N12345', 'Toy tricycle classification', '本裁定明确儿童三轮车的 HTS 归类，依据通用解释规则 (GIR) 对车身与轮组分别判定。', '9503.00.0000', '["9503.00.0000"]', 2023, 'https://rulings.cbp.gov/ruling/N12345', '2023-05-12', 'active', 0, '', 0),

  ('N23456', 'Stuffed plush toy dog', '毛绒玩具狗的归类裁定，确认其归入 9503 章并适用最惠国税率。', '9503.00.0000', '["9503.00.0000"]', 2022, 'https://rulings.cbp.gov/ruling/N23456', '2022-08-03', 'active', 0, '', 0),

  ('N34567', 'Revoked: leather wallet', '原关于皮革钱包的裁定已被撤销，新的归类指引见后续公告。', '4202.31.0000', '["4202.31.0000"]', 2021, 'https://rulings.cbp.gov/ruling/N34567', '2021-02-19', 'revoked', 0, '', 0),

  ('HQ98765', 'Multifunction wearable device', '多功能可穿戴设备的归类，涉及无线通信与数据处理功能的协调。', '8517.62.0090', '["8517.62.0090","8517.69.0000"]', 2024, 'https://rulings.cbp.gov/ruling/HQ98765', '2024-01-30', 'active', 0, '', 0),

  ('NY56789', 'Ceramic dinner plate set', '陶瓷餐盘套装的归类裁定，明确其材质与用途决定税号。', '6911.10.0000', '["6911.10.0000"]', 2020, 'https://rulings.cbp.gov/ruling/NY56789', '2020-11-11', 'active', 0, '', 0),

  ('N45678', 'Bicycle helmet', '自行车头盔的归类，确认其归入 6506 防护头盔税号。', '6506.10.0000', '["6506.10.0000"]', 2019, 'https://rulings.cbp.gov/ruling/N45678', '2019-07-22', 'active', 0, '', 0),

  ('N11111', 'Revoked: solar garden light', '关于太阳能庭院灯的裁定已撤销，原归类结论不再适用。', '9405.50.0000', '["9405.50.0000"]', 2023, 'https://rulings.cbp.gov/ruling/N11111', '2023-09-15', 'revoked', 0, '', 0),

  ('N22222', 'Wireless earbuds', '真无线耳机的归类，明确其作为通信附件归入 8518 章。', '8518.30.0000', '["8518.30.0000"]', 2024, 'https://rulings.cbp.gov/ruling/N22222', '2024-03-08', 'active', 0, '', 0),

  ('N33333', 'PARSE_FAILED sample: smart speaker', '本条目在爬虫解析阶段失败，description 缺失。', '8518.22.0000', '["8518.22.0000"]', 2022, 'https://rulings.cbp.gov/ruling/N33333', '2022-04-01', 'active', 1, 'HTML structure changed, description block not found', 0),

  ('N44444', 'PARSE_FAILED sample: power bank', '本条目在抓取详情页时超时，解析失败。', '8507.60.0000', '["8507.60.0000"]', 2023, 'https://rulings.cbp.gov/ruling/N44444', '2023-06-27', 'active', 1, 'Timeout fetching detail page', 0),

  ('N55555', 'Cotton t-shirt', '纯棉 T 恤的归类，确认其纺织纤维成分与针织工艺对应的税号。', '6109.10.0000', '["6109.10.0000"]', 2021, 'https://rulings.cbp.gov/ruling/N55555', '2021-10-05', 'active', 0, '', 0),

  ('N66666', 'Kitchen knife block set', '刀具套装归类，刀具与木座分别归类后整体按主要特征判定。', '8211.91.0000', '["8211.91.0000","4419.00.0000"]', 2020, 'https://rulings.cbp.gov/ruling/N66666', '2020-05-18', 'active', 0, '', 0),

  ('N77777', 'Revoked: bamboo cutting board', '竹制砧板裁定已撤销。', '4419.11.0000', '["4419.11.0000"]', 2019, 'https://rulings.cbp.gov/ruling/N77777', '2019-12-02', 'revoked', 0, '', 0),

  ('N88888', 'Packaged snack crackers', '预包装饼干零食的归类，确认其食品属性与包装形式。', '1905.31.0000', '["1905.31.0000"]', 2024, 'https://rulings.cbp.gov/ruling/N88888', '2024-02-14', 'active', 0, '', 0),

  ('N99999', 'CNC milling machine part', '数控机床配件的归类，明确其专用零件属性。', '8466.93.0000', '["8466.93.0000"]', 2023, 'https://rulings.cbp.gov/ruling/N99999', '2023-11-09', 'active', 0, '', 0),

  ('N10101', 'Electric vehicle charger', '电动汽车充电桩的归类，确认其功率转换功能对应税号。', '8504.40.0000', '["8504.40.0000"]', 2022, 'https://rulings.cbp.gov/ruling/N10101', '2022-07-21', 'active', 0, '', 0),

  ('N12121', 'Revoked: plastic storage bin', '塑料收纳箱裁定已撤销，重新归类见补充文件。', '3923.10.0000', '["3923.10.0000"]', 2024, 'https://rulings.cbp.gov/ruling/N12121', '2024-04-25', 'revoked', 0, '', 0);
