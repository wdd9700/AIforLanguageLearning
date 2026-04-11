-- =====================================================
-- AI外语学习系统 - PostgreSQL 初始化脚本
-- 版本: 1.0.0
-- 描述: 创建扩展、表结构、索引、触发器和示例数据
-- =====================================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =====================================================
-- 表结构定义
-- =====================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    avatar_url VARCHAR(500),
    native_language VARCHAR(10) DEFAULT 'zh',
    learning_language VARCHAR(10) DEFAULT 'en',
    proficiency_level VARCHAR(20) DEFAULT 'beginner',
    daily_goal_minutes INTEGER DEFAULT 30,
    streak_days INTEGER DEFAULT 0,
    total_learning_minutes INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 词汇表
CREATE TABLE IF NOT EXISTS vocabulary (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    word VARCHAR(255) NOT NULL,
    language VARCHAR(10) NOT NULL,
    pronunciation VARCHAR(255),
    part_of_speech VARCHAR(50),
    difficulty_level INTEGER DEFAULT 1 CHECK (difficulty_level BETWEEN 1 AND 5),
    frequency_rank INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(word, language)
);

-- 词汇定义表
CREATE TABLE IF NOT EXISTS vocabulary_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_id UUID NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    definition TEXT NOT NULL,
    language VARCHAR(10) NOT NULL,
    example_sentence TEXT,
    example_translation TEXT,
    source VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 同义词关系表
CREATE TABLE IF NOT EXISTS synonym_relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_id_1 UUID NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    vocabulary_id_2 UUID NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    relation_strength DECIMAL(3,2) DEFAULT 1.00 CHECK (relation_strength BETWEEN 0 AND 1),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vocabulary_id_1, vocabulary_id_2)
);

-- 标签表
CREATE TABLE IF NOT EXISTS tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#3498db',
    is_system BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, category, language)
);

-- 词汇标签关联表
CREATE TABLE IF NOT EXISTS vocabulary_tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vocabulary_id UUID NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(vocabulary_id, tag_id)
);

-- 学习会话表
CREATE TABLE IF NOT EXISTS learning_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_type VARCHAR(50) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    duration_minutes INTEGER,
    score INTEGER,
    feedback TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 用户词汇学习进度表
CREATE TABLE IF NOT EXISTS user_vocabulary_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_id UUID NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'new' CHECK (status IN ('new', 'learning', 'review', 'mastered')),
    mastery_level INTEGER DEFAULT 0 CHECK (mastery_level BETWEEN 0 AND 100),
    review_count INTEGER DEFAULT 0,
    correct_count INTEGER DEFAULT 0,
    incorrect_count INTEGER DEFAULT 0,
    last_reviewed_at TIMESTAMP WITH TIME ZONE,
    next_review_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, vocabulary_id)
);

-- 发音练习记录表
CREATE TABLE IF NOT EXISTS pronunciation_practice (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    vocabulary_id UUID REFERENCES vocabulary(id) ON DELETE SET NULL,
    audio_url VARCHAR(500),
    recognized_text TEXT,
    accuracy_score DECIMAL(5,2),
    fluency_score DECIMAL(5,2),
    completeness_score DECIMAL(5,2),
    pronunciation_score DECIMAL(5,2),
    practiced_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- AI对话记录表
CREATE TABLE IF NOT EXISTS ai_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID NOT NULL,
    message_role VARCHAR(20) NOT NULL CHECK (message_role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    audio_url VARCHAR(500),
    emotion_analysis JSONB,
    grammar_feedback JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- =====================================================
-- 索引创建
-- =====================================================

-- 用户表索引
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- 词汇表索引
CREATE INDEX IF NOT EXISTS idx_vocabulary_word ON vocabulary(word);
CREATE INDEX IF NOT EXISTS idx_vocabulary_language ON vocabulary(language);
CREATE INDEX IF NOT EXISTS idx_vocabulary_difficulty ON vocabulary(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_vocabulary_frequency ON vocabulary(frequency_rank);
CREATE INDEX IF NOT EXISTS idx_vocabulary_word_trgm ON vocabulary USING gin(word gin_trgm_ops);

-- 词汇定义表索引
CREATE INDEX IF NOT EXISTS idx_vocab_defs_vocab_id ON vocabulary_definitions(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_vocab_defs_language ON vocabulary_definitions(language);

-- 同义词关系表索引
CREATE INDEX IF NOT EXISTS idx_synonyms_v1 ON synonym_relations(vocabulary_id_1);
CREATE INDEX IF NOT EXISTS idx_synonyms_v2 ON synonym_relations(vocabulary_id_2);

-- 标签表索引
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_tags_category ON tags(category);
CREATE INDEX IF NOT EXISTS idx_tags_language ON tags(language);

-- 词汇标签关联表索引
CREATE INDEX IF NOT EXISTS idx_vocab_tags_vocab_id ON vocabulary_tags(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_vocab_tags_tag_id ON vocabulary_tags(tag_id);

-- 学习会话表索引
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON learning_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON learning_sessions(started_at);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON learning_sessions(session_type);

-- 用户词汇学习进度表索引
CREATE INDEX IF NOT EXISTS idx_uvp_user_id ON user_vocabulary_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_uvp_vocab_id ON user_vocabulary_progress(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_uvp_status ON user_vocabulary_progress(status);
CREATE INDEX IF NOT EXISTS idx_uvp_next_review ON user_vocabulary_progress(next_review_at);

-- 发音练习记录表索引
CREATE INDEX IF NOT EXISTS idx_pronunciation_user_id ON pronunciation_practice(user_id);
CREATE INDEX IF NOT EXISTS idx_pronunciation_vocab_id ON pronunciation_practice(vocabulary_id);
CREATE INDEX IF NOT EXISTS idx_pronunciation_practiced_at ON pronunciation_practice(practiced_at);

-- AI对话记录表索引
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON ai_conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON ai_conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON ai_conversations(created_at);

-- =====================================================
-- 触发器函数：自动更新 updated_at
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为所有需要自动更新 updated_at 的表创建触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocabulary_updated_at BEFORE UPDATE ON vocabulary
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocab_defs_updated_at BEFORE UPDATE ON vocabulary_definitions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tags_updated_at BEFORE UPDATE ON tags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vocab_tags_updated_at BEFORE UPDATE ON vocabulary_tags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_learning_sessions_updated_at BEFORE UPDATE ON learning_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_uvp_updated_at BEFORE UPDATE ON user_vocabulary_progress
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- 插入示例标签数据
-- =====================================================

INSERT INTO tags (name, category, language, description, color, is_system) VALUES
-- 主题标签
('business', 'topic', 'en', '商务英语', '#e74c3c', true),
('travel', 'topic', 'en', '旅游英语', '#3498db', true),
('daily', 'topic', 'en', '日常生活', '#2ecc71', true),
('academic', 'topic', 'en', '学术英语', '#9b59b6', true),
('technology', 'topic', 'en', '科技英语', '#f39c12', true),

-- 难度标签
('beginner', 'difficulty', 'en', '初级词汇', '#27ae60', true),
('intermediate', 'difficulty', 'en', '中级词汇', '#f1c40f', true),
('advanced', 'difficulty', 'en', '高级词汇', '#e67e22', true),

-- 词性标签
('noun', 'pos', 'en', '名词', '#1abc9c', true),
('verb', 'pos', 'en', '动词', '#e74c3c', true),
('adjective', 'pos', 'en', '形容词', '#3498db', true),
('adverb', 'pos', 'en', '副词', '#9b59b6', true),
('phrase', 'pos', 'en', '短语', '#f39c12', true),

-- 考试标签
('cet4', 'exam', 'en', '大学英语四级', '#16a085', true),
('cet6', 'exam', 'en', '大学英语六级', '#2980b9', true),
('ielts', 'exam', 'en', '雅思', '#8e44ad', true),
('toefl', 'exam', 'en', '托福', '#c0392b', true),
('gre', 'exam', 'en', 'GRE', '#d35400', true)
ON CONFLICT (name, category, language) DO NOTHING;

-- =====================================================
-- 插入示例词汇数据
-- =====================================================

-- 插入词汇
INSERT INTO vocabulary (word, language, pronunciation, part_of_speech, difficulty_level, frequency_rank) VALUES
('hello', 'en', '/həˈloʊ/', 'interjection', 1, 100),
('world', 'en', '/wɜːrld/', 'noun', 1, 150),
('computer', 'en', '/kəmˈpjuːtər/', 'noun', 2, 500),
('algorithm', 'en', '/ˈælɡərɪðəm/', 'noun', 4, 2000),
('serendipity', 'en', '/ˌserənˈdɪpəti/', 'noun', 5, 5000),
('entrepreneur', 'en', '/ˌɑːntrəprəˈnɜːr/', 'noun', 4, 1800),
('innovation', 'en', '/ˌɪnəˈveɪʃn/', 'noun', 3, 800),
('collaborate', 'en', '/kəˈlæbəreɪt/', 'verb', 3, 1200),
('sustainable', 'en', '/səˈsteɪnəbl/', 'adjective', 3, 1500),
('perspective', 'en', '/pərˈspektɪv/', 'noun', 3, 900)
ON CONFLICT (word, language) DO NOTHING;

-- 插入词汇定义
INSERT INTO vocabulary_definitions (vocabulary_id, definition, language, example_sentence, example_translation)
SELECT 
    v.id,
    CASE v.word
        WHEN 'hello' THEN '用于问候或引起注意的感叹词'
        WHEN 'world' THEN '地球；世界；全世界的人'
        WHEN 'computer' THEN '计算机；电脑；电子计算机'
        WHEN 'algorithm' THEN '算法；计算程序；规则系统'
        WHEN 'serendipity' THEN '意外发现珍奇事物的本领；机缘凑巧'
        WHEN 'entrepreneur' THEN '企业家；创业者；承包人'
        WHEN 'innovation' THEN '创新；革新；新方法'
        WHEN 'collaborate' THEN '合作；协作；通敌'
        WHEN 'sustainable' THEN '可持续的；能维持的；能承受的'
        WHEN 'perspective' THEN '观点；远景；透视法'
    END,
    'zh',
    CASE v.word
        WHEN 'hello' THEN 'Hello, how are you today?'
        WHEN 'world' THEN 'The world is becoming more connected.'
        WHEN 'computer' THEN 'I need to buy a new computer.'
        WHEN 'algorithm' THEN 'This algorithm solves the problem efficiently.'
        WHEN 'serendipity' THEN 'Finding this job was pure serendipity.'
        WHEN 'entrepreneur' THEN 'He is a successful entrepreneur in tech.'
        WHEN 'innovation' THEN 'Innovation drives economic growth.'
        WHEN 'collaborate' THEN 'We need to collaborate on this project.'
        WHEN 'sustainable' THEN 'We need sustainable energy solutions.'
        WHEN 'perspective' THEN 'From my perspective, this is a good idea.'
    END,
    CASE v.word
        WHEN 'hello' THEN '你好，你今天怎么样？'
        WHEN 'world' THEN '世界正变得更加紧密相连。'
        WHEN 'computer' THEN '我需要买一台新电脑。'
        WHEN 'algorithm' THEN '这个算法高效地解决了问题。'
        WHEN 'serendipity' THEN '找到这份工作是纯粹的机缘巧合。'
        WHEN 'entrepreneur' THEN '他是科技领域成功的企业家。'
        WHEN 'innovation' THEN '创新推动经济增长。'
        WHEN 'collaborate' THEN '我们需要在这个项目上合作。'
        WHEN 'sustainable' THEN '我们需要可持续的能源解决方案。'
        WHEN 'perspective' THEN '从我的角度来看，这是个好主意。'
    END
FROM vocabulary v
WHERE v.word IN ('hello', 'world', 'computer', 'algorithm', 'serendipity', 
                 'entrepreneur', 'innovation', 'collaborate', 'sustainable', 'perspective')
ON CONFLICT DO NOTHING;

-- 插入英文定义
INSERT INTO vocabulary_definitions (vocabulary_id, definition, language, example_sentence)
SELECT 
    v.id,
    CASE v.word
        WHEN 'hello' THEN 'used as a greeting or to begin a telephone conversation'
        WHEN 'world' THEN 'the earth, together with all of its countries and peoples'
        WHEN 'computer' THEN 'an electronic device for storing and processing data'
        WHEN 'algorithm' THEN 'a process or set of rules to be followed in calculations'
        WHEN 'serendipity' THEN 'the occurrence of events by chance in a happy way'
        WHEN 'entrepreneur' THEN 'a person who organizes and operates a business'
        WHEN 'innovation' THEN 'the action or process of innovating; a new method'
        WHEN 'collaborate' THEN 'work jointly on an activity or project'
        WHEN 'sustainable' THEN 'able to be maintained at a certain rate or level'
        WHEN 'perspective' THEN 'a particular attitude toward or way of regarding something'
    END,
    'en',
    CASE v.word
        WHEN 'hello' THEN 'Hello, nice to meet you.'
        WHEN 'world' THEN 'He wants to travel around the world.'
        WHEN 'computer' THEN 'She works on a computer all day.'
        WHEN 'algorithm' THEN 'The search engine uses a complex algorithm.'
        WHEN 'serendipity' THEN 'Meeting her was pure serendipity.'
        WHEN 'entrepreneur' THEN 'The entrepreneur started three companies.'
        WHEN 'innovation' THEN 'The company encourages innovation.'
        WHEN 'collaborate' THEN 'The two artists decided to collaborate.'
        WHEN 'sustainable' THEN 'We need sustainable development.'
        WHEN 'perspective' THEN 'Try to see it from my perspective.'
    END
FROM vocabulary v
WHERE v.word IN ('hello', 'world', 'computer', 'algorithm', 'serendipity', 
                 'entrepreneur', 'innovation', 'collaborate', 'sustainable', 'perspective')
ON CONFLICT DO NOTHING;

-- =====================================================
-- 插入示例同义词关系
-- =====================================================

-- 获取词汇ID并建立同义词关系
WITH vocab_ids AS (
    SELECT id, word FROM vocabulary WHERE word IN ('innovation', 'perspective')
)
INSERT INTO synonym_relations (vocabulary_id_1, vocabulary_id_2, relation_strength)
SELECT v1.id, v2.id, 0.85
FROM vocab_ids v1, vocab_ids v2
WHERE v1.word = 'innovation' AND v2.word = 'perspective'
ON CONFLICT (vocabulary_id_1, vocabulary_id_2) DO NOTHING;

-- =====================================================
-- 插入词汇标签关联
-- =====================================================

-- 为词汇添加标签
INSERT INTO vocabulary_tags (vocabulary_id, tag_id)
SELECT v.id, t.id
FROM vocabulary v
CROSS JOIN tags t
WHERE 
    (v.word = 'hello' AND t.name = 'beginner' AND t.category = 'difficulty')
    OR (v.word = 'hello' AND t.name = 'daily' AND t.category = 'topic')
    OR (v.word = 'world' AND t.name = 'beginner' AND t.category = 'difficulty')
    OR (v.word = 'computer' AND t.name = 'technology' AND t.category = 'topic')
    OR (v.word = 'computer' AND t.name = 'intermediate' AND t.category = 'difficulty')
    OR (v.word = 'computer' AND t.name = 'noun' AND t.category = 'pos')
    OR (v.word = 'algorithm' AND t.name = 'technology' AND t.category = 'topic')
    OR (v.word = 'algorithm' AND t.name = 'advanced' AND t.category = 'difficulty')
    OR (v.word = 'algorithm' AND t.name = 'noun' AND t.category = 'pos')
    OR (v.word = 'entrepreneur' AND t.name = 'business' AND t.category = 'topic')
    OR (v.word = 'entrepreneur' AND t.name = 'advanced' AND t.category = 'difficulty')
    OR (v.word = 'innovation' AND t.name = 'business' AND t.category = 'topic')
    OR (v.word = 'innovation' AND t.name = 'intermediate' AND t.category = 'difficulty')
    OR (v.word = 'collaborate' AND t.name = 'business' AND t.category = 'topic')
    OR (v.word = 'collaborate' AND t.name = 'verb' AND t.category = 'pos')
    OR (v.word = 'sustainable' AND t.name = 'adjective' AND t.category = 'pos')
    OR (v.word = 'perspective' AND t.name = 'noun' AND t.category = 'pos')
ON CONFLICT (vocabulary_id, tag_id) DO NOTHING;

-- =====================================================
-- 创建视图
-- =====================================================

-- 词汇完整信息视图
CREATE OR REPLACE VIEW vocabulary_full_info AS
SELECT 
    v.id,
    v.word,
    v.language,
    v.pronunciation,
    v.part_of_speech,
    v.difficulty_level,
    v.frequency_rank,
    vd_zh.definition AS definition_zh,
    vd_zh.example_sentence AS example_zh,
    vd_zh.example_translation AS example_translation_zh,
    vd_en.definition AS definition_en,
    vd_en.example_sentence AS example_en,
    ARRAY_AGG(DISTINCT t.name) FILTER (WHERE t.name IS NOT NULL) AS tags,
    v.created_at,
    v.updated_at
FROM vocabulary v
LEFT JOIN vocabulary_definitions vd_zh ON v.id = vd_zh.vocabulary_id AND vd_zh.language = 'zh'
LEFT JOIN vocabulary_definitions vd_en ON v.id = vd_en.vocabulary_id AND vd_en.language = 'en'
LEFT JOIN vocabulary_tags vt ON v.id = vt.vocabulary_id
LEFT JOIN tags t ON vt.tag_id = t.id
GROUP BY v.id, vd_zh.definition, vd_zh.example_sentence, vd_zh.example_translation,
         vd_en.definition, vd_en.example_sentence;

-- 用户学习统计视图
CREATE OR REPLACE VIEW user_learning_stats AS
SELECT 
    u.id AS user_id,
    u.username,
    u.display_name,
    COUNT(DISTINCT uvp.vocabulary_id) AS total_vocabulary_learned,
    COUNT(DISTINCT CASE WHEN uvp.status = 'mastered' THEN uvp.vocabulary_id END) AS mastered_count,
    COUNT(DISTINCT CASE WHEN uvp.status = 'learning' THEN uvp.vocabulary_id END) AS learning_count,
    COUNT(DISTINCT CASE WHEN uvp.status = 'review' THEN uvp.vocabulary_id END) AS review_count,
    COUNT(DISTINCT ls.id) AS total_sessions,
    COALESCE(SUM(ls.duration_minutes), 0) AS total_learning_minutes,
    u.streak_days,
    u.last_login_at
FROM users u
LEFT JOIN user_vocabulary_progress uvp ON u.id = uvp.user_id
LEFT JOIN learning_sessions ls ON u.id = ls.user_id
GROUP BY u.id, u.username, u.display_name, u.streak_days, u.last_login_at;

-- =====================================================
-- 初始化完成
-- =====================================================

SELECT 'Database initialization completed successfully!' AS status;
