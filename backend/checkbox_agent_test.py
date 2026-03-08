"""
체크박스 에이전트 독립 테스트 스크립트
Flask 없이 독립적으로 실행 가능
"""

import sys
import os
from checkbox_agent import (
    load_structured_output,
    process_checkbox_by_coordinate,
    get_cached_structured_output,
    get_logs,
    add_log
)

def print_logs():
    """로그 출력"""
    logs = get_logs()
    print("\n" + "="*80)
    print("📋 에이전트 로그")
    print("="*80)
    for log in logs[-20:]:  # 최근 20개만
        icon = "ℹ️" if log['level'] == 'info' else "✅" if log['level'] == 'success' else "❌" if log['level'] == 'error' else "⚠️"
        print(f"[{log['timestamp']}] {icon} {log['message']}")
    print("="*80 + "\n")

def main():
    """메인 함수"""
    print("="*80)
    print("☑️ 체크박스 에이전트 독립 테스트")
    print("="*80)
    
    # 1. structured_output.json 로드
    print("\n1️⃣ structured_output.json 로드 중...")
    default_path = os.path.join(os.path.dirname(__file__), 'structured_output.json')
    
    if not os.path.exists(default_path):
        print(f"❌ 파일을 찾을 수 없습니다: {default_path}")
        print("파일 경로를 입력하세요 (또는 Enter로 종료): ", end="")
        filepath = input().strip()
        if not filepath:
            return
        if not os.path.exists(filepath):
            print(f"❌ 파일을 찾을 수 없습니다: {filepath}")
            return
    else:
        filepath = default_path
    
    structured_output = load_structured_output(filepath)
    
    if not structured_output:
        print("❌ structured_output.json 로드 실패")
        return
    
    print(f"✅ structured_output.json 로드 완료")
    print_logs()
    
    # 2. 좌표 입력 받기
    print("\n2️⃣ 좌표 입력")
    print("형식: X1 Y1 X2 Y2 (예: 1398 2114 1409 2125)")
    print("여러 개 입력 시 한 줄에 하나씩 입력하고, 빈 줄 입력 시 처리 시작")
    print("-" * 80)
    
    coordinates = []
    while True:
        try:
            line = input("좌표 입력 (또는 Enter로 처리 시작): ").strip()
            if not line:
                break
            
            parts = line.split()
            if len(parts) == 4:
                try:
                    x1, y1, x2, y2 = map(float, parts)
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    coordinates.append({
                        'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2,
                        'center_x': center_x, 'center_y': center_y
                    })
                    print(f"  ✅ 좌표 추가: ({center_x:.1f}, {center_y:.1f})")
                except ValueError:
                    print("  ❌ 잘못된 형식입니다. 숫자 4개를 입력하세요.")
            else:
                print("  ❌ 잘못된 형식입니다. X1 Y1 X2 Y2 형식으로 입력하세요.")
        except KeyboardInterrupt:
            print("\n\n취소되었습니다.")
            return
        except EOFError:
            break
    
    if not coordinates:
        print("❌ 좌표가 입력되지 않았습니다.")
        return
    
    print(f"\n총 {len(coordinates)}개 좌표 입력됨")
    
    # 3. 좌표 처리
    print("\n3️⃣ 체크박스 처리 시작...")
    print("-" * 80)
    
    results = []
    for i, coord in enumerate(coordinates, 1):
        print(f"\n[{i}/{len(coordinates)}] 좌표 처리: ({coord['center_x']:.1f}, {coord['center_y']:.1f})")
        
        result = process_checkbox_by_coordinate(coord['center_x'], coord['center_y'])
        
        if result.get('success') and result.get('updated'):
            print(f"  ✅ 성공: {result['checkbox']['name']} (방법: {result.get('method', 'unknown')}, 거리: {result.get('distance', 0):.2f})")
            results.append({
                'index': i,
                'success': True,
                'checkbox': result['checkbox'],
                'path': result['path'],
                'method': result.get('method', 'unknown'),
                'distance': result.get('distance', 0)
            })
        else:
            print(f"  ❌ 실패: {result.get('error', '알 수 없는 오류')}")
            results.append({
                'index': i,
                'success': False,
                'error': result.get('error', '알 수 없는 오류')
            })
    
    # 4. 결과 요약
    print("\n" + "="*80)
    print("📊 처리 결과 요약")
    print("="*80)
    
    success_count = sum(1 for r in results if r['success'])
    fail_count = len(results) - success_count
    
    print(f"전체: {len(results)}개")
    print(f"성공: {success_count}개")
    print(f"실패: {fail_count}개")
    
    print("\n상세 결과:")
    for result in results:
        if result['success']:
            print(f"  [{result['index']}] ✅ {result['checkbox']['name']} (방법: {result['method']}, 거리: {result['distance']:.2f})")
        else:
            print(f"  [{result['index']}] ❌ {result['error']}")
    
    # 5. 로그 출력
    print_logs()
    
    # 6. 수정된 JSON 저장 여부 확인
    structured_output = get_cached_structured_output()
    if structured_output:
        print("\n4️⃣ 수정된 JSON 저장")
        print("수정된 structured_output.json을 저장하시겠습니까? (y/n): ", end="")
        try:
            save = input().strip().lower()
            if save == 'y':
                output_path = os.path.join(os.path.dirname(__file__), 'structured_output_updated.json')
                import json
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(structured_output, f, ensure_ascii=False, indent=2)
                print(f"✅ 저장 완료: {output_path}")
        except (KeyboardInterrupt, EOFError):
            print("\n저장 취소됨")
    
    print("\n" + "="*80)
    print("✅ 처리 완료!")
    print("="*80)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램이 중단되었습니다.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

