insert into terms (source, target, mode, note)
values
    ('풍차돌리기', 'Pungchadolligi', 'translate', '팀명'),
    ('글로시', 'Glossy', 'translate', '서비스명'),
    ('MVP', null, 'preserve', '제품 개발 용어'),
    ('QA', null, 'preserve', '품질 보증'),
    ('PR', null, 'preserve', 'Pull Request로 해석해야 하는 개발 약어')
on conflict do nothing;

insert into contacts (name, company, role, note)
values
    ('Kevin Tran', 'Acme', 'PM', '정중하고 간결한 비즈니스 표현'),
    ('Sarah Kim', 'Northstar', 'Director', '격식을 갖춘 이메일 표현'),
    ('Alex Morgan', 'Acme', 'Engineer', '짧고 직접적인 협업 표현')
on conflict do nothing;
